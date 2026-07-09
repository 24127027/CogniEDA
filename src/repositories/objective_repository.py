"""Persistence access for Objective FCOs."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from db.models import ObjectiveRecord
from pydantic import BaseModel, ConfigDict
from repositories.common import apply_update, record_to_schema, schema_to_record_payload
from schemas.artifacts import Objective
from schemas.enums import ObjectiveStatus
from schemas.provenance import ObjectiveRevision
from sqlmodel import Session, desc, select

if TYPE_CHECKING:
    from repositories.objective_revision_repository import ObjectiveRevisionRepository


OBJECTIVE_REVISION_FIELDS = ("title", "statement", "status")


class ObjectiveUpdate(BaseModel):
    """Typed mutable fields for Objective lifecycle and wording changes."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    statement: str | None = None
    status: ObjectiveStatus | None = None
    updated_at: datetime | None = None


def changed_objective_fields(previous: Objective, updated: Objective) -> list[str]:
    """Return persisted Objective fields whose values changed."""

    return [
        field_name
        for field_name in OBJECTIVE_REVISION_FIELDS
        if getattr(previous, field_name) != getattr(updated, field_name)
    ]


def build_objective_revision(
    previous: Objective,
    updated: Objective,
    *,
    revision_reason: str | None = None,
    planner_operation_id: UUID | str | None = None,
    user_decision_id: UUID | str | None = None,
    created_by: str | None = None,
) -> ObjectiveRevision | None:
    """Build a minimal ObjectiveRevision for a real Objective value change."""

    changed_fields = changed_objective_fields(previous, updated)
    if not changed_fields:
        return None
    return ObjectiveRevision(
        objective_id=previous.objective_id,
        previous_title=previous.title,
        previous_description=previous.statement,
        previous_lifecycle_state=previous.status,
        new_title=updated.title,
        new_description=updated.statement,
        new_lifecycle_state=updated.status,
        changed_fields=changed_fields,
        revision_reason=revision_reason,
        planner_operation_id=(
            str(planner_operation_id) if planner_operation_id is not None else None
        ),
        user_decision_id=str(user_decision_id) if user_decision_id is not None else None,
        created_by=created_by,
    )


class ObjectiveRepository:
    """Repository for workspace-local Objective records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, objective: Objective) -> Objective:
        """Persist and return a new Objective."""

        record = ObjectiveRecord(**schema_to_record_payload(objective))
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(Objective, record)

    def get_by_id(self, objective_id: UUID) -> Objective | None:
        """Return an Objective by primary id if it exists."""

        record = self._session.get(ObjectiveRecord, objective_id)
        if record is None:
            return None
        return record_to_schema(Objective, record)

    def list(self, *, status: ObjectiveStatus | None = None) -> list[Objective]:
        """List objectives with an optional lifecycle filter."""

        statement = select(ObjectiveRecord).order_by(desc(ObjectiveRecord.updated_at))
        if status is not None:
            statement = statement.where(ObjectiveRecord.status == status)
        records = self._session.exec(statement).all()
        return [record_to_schema(Objective, record) for record in records]

    def update(
        self,
        objective_id: UUID,
        update: ObjectiveUpdate,
        *,
        revision_repository: ObjectiveRevisionRepository | None = None,
        revision_reason: str | None = None,
        planner_operation_id: UUID | str | None = None,
        user_decision_id: UUID | str | None = None,
        created_by: str | None = None,
    ) -> Objective | None:
        """Apply an allowed Objective transition, optionally recording revision provenance."""

        record = self._session.get(ObjectiveRecord, objective_id)
        if record is None:
            return None
        previous = record_to_schema(Objective, record)
        apply_update(record, update)
        updated = record_to_schema(Objective, record)
        self._session.add(record)
        revision = None
        if revision_repository is not None:
            revision = build_objective_revision(
                previous,
                updated,
                revision_reason=revision_reason,
                planner_operation_id=planner_operation_id,
                user_decision_id=user_decision_id,
                created_by=created_by,
            )
        if revision is not None and revision_repository is not None:
            revision_repository.create(revision)
        else:
            self._session.commit()
        self._session.refresh(record)
        return record_to_schema(Objective, record)
