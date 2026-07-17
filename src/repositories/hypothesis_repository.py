"""Persistence access for Hypothesis FCOs."""

from __future__ import annotations

import builtins
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session, desc, select

from db.models import DataProfileRecord, HypothesisRecord, TaskRecord
from repositories.common import apply_update, record_to_schema, schema_to_record_payload
from schemas.artifacts import Hypothesis, Task
from schemas.enums import DataProfileLifecycleState, HypothesisStatus

HYPOTHESIS_JSON_FIELDS = {"variables"}


class HypothesisUpdate(BaseModel):
    """Typed mutable fields for hypothesis lifecycle transitions."""

    statement: str | None = None
    variables: list[str] | None = None
    scope: str | None = None
    validation_method: str | None = None
    evidence_expectation: str | None = None
    status: HypothesisStatus | None = None
    updated_at: datetime | None = None


class HypothesisRepository:
    """Repository for atomic hypothesis test contracts."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, hypothesis: Hypothesis) -> Hypothesis:
        """Persist and return a new Hypothesis."""

        record = self.stage_create(hypothesis)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(Hypothesis, record)

    def stage_create(self, hypothesis: Hypothesis) -> HypothesisRecord:
        """Validate and add a Hypothesis without committing the shared session."""

        self._validate_hypothesis_admission(hypothesis)
        record = HypothesisRecord(
            **schema_to_record_payload(hypothesis, json_fields=HYPOTHESIS_JSON_FIELDS)
        )
        self._session.add(record)
        return record

    def _validate_hypothesis_admission(self, hypothesis: Hypothesis) -> None:
        task_record = self._session.get(TaskRecord, hypothesis.task_id)
        if task_record is None:
            raise ValueError("Hypothesis creation requires an existing source Task.")

        task = record_to_schema(Task, task_record)
        if task.profile_id != hypothesis.profile_id:
            raise ValueError("Hypothesis profile_id must match its source Task profile_id.")

        profile_record = self._session.get(DataProfileRecord, hypothesis.profile_id)
        if profile_record is None:
            raise ValueError("Hypothesis creation requires an existing DataProfile.")
        data_profile_accepted = (
            profile_record.lifecycle_state == DataProfileLifecycleState.ACTIVE
            and profile_record.accepted_as_ground_truth
        )

        has_child_tasks = (
            self._session.exec(
                select(TaskRecord).where(TaskRecord.parent_task_id == hypothesis.task_id)
            ).first()
            is not None
        )
        if not task.can_generate_hypothesis(
            has_child_tasks=has_child_tasks,
            data_profile_accepted=data_profile_accepted,
        ):
            raise ValueError(
                "Only active terminal analytical Tasks using an accepted DataProfile "
                "can generate a Hypothesis."
            )

        duplicate = self._session.exec(
            select(HypothesisRecord).where(HypothesisRecord.task_id == hypothesis.task_id)
        ).first()
        if duplicate is not None:
            raise ValueError("A Task can generate exactly one Hypothesis.")

    def get_by_id(self, hypothesis_id: UUID) -> Hypothesis | None:
        """Return a hypothesis by primary id if it exists."""

        record = self._session.get(HypothesisRecord, hypothesis_id)
        if record is None:
            return None
        return record_to_schema(Hypothesis, record)

    def list(
        self,
        *,
        task_id: UUID | None = None,
        profile_id: UUID | None = None,
        status: HypothesisStatus | None = None,
    ) -> list[Hypothesis]:
        """List hypotheses by task, profile, or lifecycle state."""

        statement = select(HypothesisRecord).order_by(desc(HypothesisRecord.updated_at))
        if task_id is not None:
            statement = statement.where(HypothesisRecord.task_id == task_id)
        if profile_id is not None:
            statement = statement.where(HypothesisRecord.profile_id == profile_id)
        if status is not None:
            statement = statement.where(HypothesisRecord.status == status)
        records = self._session.exec(statement).all()
        return [record_to_schema(Hypothesis, record) for record in records]

    def list_active(self) -> builtins.list[Hypothesis]:
        """List hypotheses that can still appear in active working context."""

        active_statuses = (HypothesisStatus.PROPOSED, HypothesisStatus.TESTING)
        return [hypothesis for hypothesis in self.list() if hypothesis.status in active_statuses]

    def list_for_profile(self, profile_id: UUID) -> builtins.list[Hypothesis]:
        """List hypotheses scoped to a DataProfile."""

        return self.list(profile_id=profile_id)

    def update(self, hypothesis_id: UUID, update: HypothesisUpdate) -> Hypothesis | None:
        """Apply an allowed hypothesis lifecycle transition."""

        record = self._session.get(HypothesisRecord, hypothesis_id)
        if record is None:
            return None
        apply_update(record, update, json_fields=HYPOTHESIS_JSON_FIELDS)
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(Hypothesis, record)
