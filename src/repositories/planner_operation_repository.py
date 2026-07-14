"""Persistence access for planner-produced pending state transitions."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, asc, select

from db.models import PlannerOperationRecord
from repositories.common import record_to_schema, schema_to_record_payload
from schemas.enums import PlannerOperationApprovalState
from schemas.planner_operations import PlannerOperation

PLANNER_OPERATION_JSON_FIELDS = {"payload"}


class PlannerOperationRepository:
    """Repository for durable PlannerOperation records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, operation: PlannerOperation) -> PlannerOperation:
        """Persist and return a new PlannerOperation."""

        record = self.stage_create(operation)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(PlannerOperation, record)

    def stage_create(self, operation: PlannerOperation) -> PlannerOperationRecord:
        """Add an operation to the current transaction without committing it."""

        record = PlannerOperationRecord(
            **schema_to_record_payload(
                operation,
                json_fields=PLANNER_OPERATION_JSON_FIELDS,
            )
        )
        self._session.add(record)
        return record

    def get_by_id(self, operation_id: UUID) -> PlannerOperation | None:
        """Return a PlannerOperation by primary id if it exists."""

        record = self._session.get(PlannerOperationRecord, operation_id)
        if record is None:
            return None
        return record_to_schema(PlannerOperation, record)

    def list(
        self,
        *,
        session_id: str | None = None,
        approval_state: PlannerOperationApprovalState | None = None,
    ) -> list[PlannerOperation]:
        """List PlannerOperations with simple skeleton-stage filters."""

        statement = (
            select(PlannerOperationRecord)
            .order_by(asc(PlannerOperationRecord.created_at))
        )
        if session_id is not None:
            statement = statement.where(PlannerOperationRecord.session_id == session_id)
        if approval_state is not None:
            statement = statement.where(
                PlannerOperationRecord.approval_state == approval_state
            )
        records = self._session.exec(statement).all()
        return [record_to_schema(PlannerOperation, record) for record in records]
