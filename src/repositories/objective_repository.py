"""Persistence and lifecycle guards for Objective FCOs."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session, asc, col, select

from db.models import (
    ObjectiveRecord,
    PlannerOperationRecord,
    TaskRecord,
    UserDecisionRecord,
)
from repositories.common import apply_update, record_to_schema, schema_to_record_payload
from repositories.objective_revision_repository import ObjectiveRevisionRepository
from schemas.artifacts import Objective
from schemas.enums import (
    ObjectiveStatus,
    PlannerOperationApprovalState,
    PlannerOperationType,
    TaskLifecycleState,
    UserDecisionStatus,
    UserDecisionType,
)
from schemas.provenance import ObjectiveRevision

OBJECTIVE_REVISION_FIELDS = ("title", "statement", "status")
UNFINISHED_TASK_STATES = {
    TaskLifecycleState.PROPOSED,
    TaskLifecycleState.ACTIVE,
    TaskLifecycleState.PAUSED,
}
ALLOWED_OBJECTIVE_TRANSITIONS = {
    ObjectiveStatus.ACTIVE: {
        ObjectiveStatus.PAUSED,
        ObjectiveStatus.COMPLETED,
        ObjectiveStatus.ARCHIVED,
    },
    ObjectiveStatus.PAUSED: {
        ObjectiveStatus.ACTIVE,
        ObjectiveStatus.COMPLETED,
        ObjectiveStatus.ARCHIVED,
    },
    ObjectiveStatus.COMPLETED: {
        ObjectiveStatus.ACTIVE,
        ObjectiveStatus.ARCHIVED,
    },
    ObjectiveStatus.ARCHIVED: {ObjectiveStatus.ACTIVE},
}


class MultipleActiveObjectivesError(RuntimeError):
    """Raised instead of silently selecting from corrupt legacy state."""


class ObjectiveUpdate(BaseModel):
    """Typed mutable fields for Objective lifecycle and wording changes."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    statement: str | None = None
    status: ObjectiveStatus | None = None


class ObjectiveMutationContext(BaseModel):
    """Required provenance and optimistic-lock input for a governed update."""

    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1)
    actor: str = Field(min_length=1)
    expected_updated_at: datetime
    planner_operation_id: UUID | None = None
    user_decision_id: UUID | None = None


def changed_objective_fields(previous: Objective, updated: Objective) -> list[str]:
    """Return changed Objective fields in a stable contract order."""

    return [
        field_name
        for field_name in OBJECTIVE_REVISION_FIELDS
        if getattr(previous, field_name) != getattr(updated, field_name)
    ]


def validate_objective_transition(previous: ObjectiveStatus, updated: ObjectiveStatus) -> None:
    """Reject lifecycle assignments that have no explicit governed meaning."""

    if previous == updated:
        return
    if updated not in ALLOWED_OBJECTIVE_TRANSITIONS[previous]:
        raise ValueError(
            f"Objective transition {previous.value} -> {updated.value} is not allowed."
        )


def build_objective_revision(
    previous: Objective,
    updated: Objective,
    *,
    context: ObjectiveMutationContext,
) -> ObjectiveRevision | None:
    """Build exact before/after provenance for a real Objective change."""

    changed_fields = changed_objective_fields(previous, updated)
    if not changed_fields:
        return None
    return ObjectiveRevision(
        objective_id=previous.objective_id,
        previous_title=previous.title,
        previous_statement=previous.statement,
        previous_status=previous.status,
        new_title=updated.title,
        new_statement=updated.statement,
        new_status=updated.status,
        changed_fields=changed_fields,
        reason=context.reason,
        planner_operation_id=context.planner_operation_id,
        user_decision_id=context.user_decision_id,
        actor=context.actor,
    )


class ObjectiveRepository:
    """Repository for the singular workspace-current Objective lifecycle."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_for_bootstrap(self, objective: Objective) -> Objective:
        """Explicit import/bootstrap bypass; normal user creation uses Planner commit."""

        record = self._stage_create_unchecked(objective)
        try:
            self._session.commit()
            self._session.refresh(record)
        except Exception:
            self._session.rollback()
            raise
        return record_to_schema(Objective, record)

    def stage_create_for_planner_commit(
        self,
        objective: Objective,
        *,
        planner_operation_id: UUID,
    ) -> ObjectiveRecord:
        """Stage creation only for its persisted approved Planner operation."""

        operation = self._session.get(PlannerOperationRecord, planner_operation_id)
        if (
            operation is None
            or operation.operation_type != PlannerOperationType.CREATE_OBJECTIVE
            or operation.approval_state != PlannerOperationApprovalState.APPROVED
        ):
            raise ValueError(
                "Objective creation requires its persisted approved PlannerOperation."
            )
        return self._stage_create_unchecked(objective)

    def _stage_create_unchecked(self, objective: Objective) -> ObjectiveRecord:
        """Stage a row after the caller has selected a governed or bootstrap path."""

        if self._session.get(ObjectiveRecord, objective.objective_id) is not None:
            raise ValueError(f"Objective already exists: {objective.objective_id}")
        record = ObjectiveRecord(**schema_to_record_payload(objective))
        self._session.add(record)
        return record

    def get_by_id(self, objective_id: UUID) -> Objective | None:
        """Return an Objective by primary id if it exists."""

        record = self._session.get(ObjectiveRecord, objective_id)
        if record is None:
            return None
        return record_to_schema(Objective, record)

    def list(self, *, status: ObjectiveStatus | None = None) -> list[Objective]:
        """List Objectives deterministically, optionally filtered by lifecycle."""

        statement = select(ObjectiveRecord).order_by(
            asc(ObjectiveRecord.created_at),
            asc(ObjectiveRecord.objective_id),
        )
        if status is not None:
            statement = statement.where(ObjectiveRecord.status == status)
        records = self._session.exec(statement).all()
        return [record_to_schema(Objective, record) for record in records]

    def get_active(self) -> Objective | None:
        """Return the unique ACTIVE Objective or expose legacy corruption."""

        statement = (
            select(ObjectiveRecord)
            .where(ObjectiveRecord.status == ObjectiveStatus.ACTIVE)
            .order_by(asc(ObjectiveRecord.objective_id))
            .limit(2)
        )
        records = self._session.exec(statement).all()
        if len(records) > 1:
            raise MultipleActiveObjectivesError(
                "Workspace contains multiple ACTIVE Objectives; repair is required."
            )
        if not records:
            return None
        return record_to_schema(Objective, records[0])

    def stage_update(
        self,
        objective_id: UUID,
        update: ObjectiveUpdate,
        *,
        context: ObjectiveMutationContext,
    ) -> ObjectiveRecord:
        """Stage one governed Objective mutation and its revision atomically."""

        record = self._session.get(ObjectiveRecord, objective_id)
        if record is None:
            raise ValueError(f"Objective does not exist: {objective_id}")
        previous = record_to_schema(Objective, record)
        if previous.updated_at != context.expected_updated_at:
            raise ValueError("Objective proposal is stale; updated_at no longer matches.")
        if not context.reason.strip() or not context.actor.strip():
            raise ValueError("Objective mutation reason and actor must be non-empty.")
        if context.planner_operation_id is not None:
            operation = self._session.get(
                PlannerOperationRecord,
                context.planner_operation_id,
            )
            if (
                operation is None
                or operation.operation_type != PlannerOperationType.UPDATE_OBJECTIVE
                or operation.approval_state != PlannerOperationApprovalState.APPROVED
            ):
                raise ValueError(
                    "Objective mutation requires its persisted approved PlannerOperation."
                )
        elif context.user_decision_id is not None:
            decision = self._session.get(UserDecisionRecord, context.user_decision_id)
            if (
                decision is None
                or decision.decision_type != UserDecisionType.OBJECTIVE_MANAGEMENT
                or decision.status != UserDecisionStatus.ACTIVE
            ):
                raise ValueError(
                    "Direct Objective mutation requires an active Objective-management "
                    "UserDecision."
                )
        else:
            raise ValueError(
                "Objective mutation requires approved PlannerOperation or UserDecision provenance."
            )

        next_status = update.status or previous.status
        validate_objective_transition(previous.status, next_status)
        if previous.status == ObjectiveStatus.ACTIVE and next_status != ObjectiveStatus.ACTIVE:
            unfinished = self._session.exec(
                select(TaskRecord.task_id).where(
                    col(TaskRecord.lifecycle_state).in_(UNFINISHED_TASK_STATES)
                )
            ).first()
            if unfinished is not None:
                raise ValueError(
                    "Cannot leave the ACTIVE Objective while unfinished Tasks exist."
                )
        if next_status == ObjectiveStatus.ACTIVE and previous.status != ObjectiveStatus.ACTIVE:
            active = self.get_active()
            if active is not None and active.objective_id != objective_id:
                raise ValueError("Another Objective is already ACTIVE.")

        apply_update(record, update)
        record.updated_at = datetime.now(UTC)
        updated = record_to_schema(Objective, record)
        revision = build_objective_revision(previous, updated, context=context)
        if revision is None:
            raise ValueError("Objective update is a no-op.")
        self._session.add(record)
        ObjectiveRevisionRepository(self._session).stage_for_objective_mutation(revision)
        return record

    def update(
        self,
        objective_id: UUID,
        update: ObjectiveUpdate,
        *,
        context: ObjectiveMutationContext,
    ) -> Objective:
        """Commit one directly governed mutation with mandatory revision provenance."""

        if context.user_decision_id is None or context.planner_operation_id is not None:
            raise ValueError(
                "Direct Objective update requires UserDecision provenance; "
                "Planner operations use the commit boundary."
            )
        try:
            record = self.stage_update(objective_id, update, context=context)
            self._session.commit()
            self._session.refresh(record)
        except Exception:
            self._session.rollback()
            raise
        return record_to_schema(Objective, record)

    def update_for_bootstrap(self, objective_id: UUID, update: ObjectiveUpdate) -> Objective:
        """Explicit import/repair bypass that intentionally creates no revision."""

        record = self._session.get(ObjectiveRecord, objective_id)
        if record is None:
            raise ValueError(f"Objective does not exist: {objective_id}")
        apply_update(record, update)
        record.updated_at = datetime.now(UTC)
        self._session.add(record)
        try:
            self._session.commit()
            self._session.refresh(record)
        except Exception:
            self._session.rollback()
            raise
        return record_to_schema(Objective, record)
