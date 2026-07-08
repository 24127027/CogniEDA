"""Persistence access for planner-produced pending state transitions."""

from __future__ import annotations

from datetime import UTC, datetime
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

        record = PlannerOperationRecord(
            **schema_to_record_payload(
                operation,
                json_fields=PLANNER_OPERATION_JSON_FIELDS,
            )
        )
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(PlannerOperation, record)

    def get_by_id(self, operation_id: UUID) -> PlannerOperation | None:
        """Return a PlannerOperation by primary id if it exists."""

        record = self._session.get(PlannerOperationRecord, operation_id)
        if record is None:
            return None
        return record_to_schema(PlannerOperation, record)

    def list_pending_operations(self, *, session_id: str | None = None) -> list[PlannerOperation]:
        """List operations still awaiting user approval."""

        return self._list_by_approval_state(
            PlannerOperationApprovalState.PENDING,
            session_id=session_id,
        )

    def list_approved_operations(
        self,
        *,
        session_id: str | None = None,
    ) -> list[PlannerOperation]:
        """List approved operations that are eligible for commit."""

        return self._list_by_approval_state(
            PlannerOperationApprovalState.APPROVED,
            session_id=session_id,
        )

    def list_committable_operations(
        self,
        *,
        session_id: str | None = None,
    ) -> list[PlannerOperation]:
        """List operations that commit is allowed to apply."""

        statement = (
            select(PlannerOperationRecord)
            .where(
                PlannerOperationRecord.approval_state.in_(
                    (
                        PlannerOperationApprovalState.APPROVED,
                        PlannerOperationApprovalState.NOT_REQUIRED,
                    )
                )
            )
            .order_by(asc(PlannerOperationRecord.created_at))
        )
        if session_id is not None:
            statement = statement.where(PlannerOperationRecord.session_id == session_id)
        records = self._session.exec(statement).all()
        return [record_to_schema(PlannerOperation, record) for record in records]

    def approve_operation(self, operation_id: UUID) -> PlannerOperation | None:
        """Approve a pending operation for commit."""

        return self._mark(
            operation_id,
            approval_state=PlannerOperationApprovalState.APPROVED,
            approved_at=datetime.now(UTC),
            error_message=None,
        )

    def reject_operation(
        self,
        operation_id: UUID,
        *,
        error_message: str | None = None,
    ) -> PlannerOperation | None:
        """Reject an operation so commit cannot mutate FCO state from it."""

        return self._mark(
            operation_id,
            approval_state=PlannerOperationApprovalState.REJECTED,
            error_message=error_message,
        )

    def mark_committed(self, operation_id: UUID) -> PlannerOperation | None:
        """Mark an operation as committed after its mutation is durably applied."""

        return self._mark(
            operation_id,
            approval_state=PlannerOperationApprovalState.COMMITTED,
            committed_at=datetime.now(UTC),
            error_message=None,
        )

    def mark_failed(
        self,
        operation_id: UUID,
        *,
        error_message: str,
    ) -> PlannerOperation | None:
        """Mark an operation as failed after commit validation or application failure."""

        return self._mark(
            operation_id,
            approval_state=PlannerOperationApprovalState.FAILED,
            error_message=error_message,
        )

    def list_operations_by_session_id(self, session_id: str) -> list[PlannerOperation]:
        """List operations produced during one planner session."""

        statement = (
            select(PlannerOperationRecord)
            .where(PlannerOperationRecord.session_id == session_id)
            .order_by(asc(PlannerOperationRecord.created_at))
        )
        records = self._session.exec(statement).all()
        return [record_to_schema(PlannerOperation, record) for record in records]

    def list_operations_by_target_object_id(
        self,
        target_object_id: UUID,
    ) -> list[PlannerOperation]:
        """List operations targeting a specific persisted object id."""

        statement = (
            select(PlannerOperationRecord)
            .where(PlannerOperationRecord.target_object_id == target_object_id)
            .order_by(asc(PlannerOperationRecord.created_at))
        )
        records = self._session.exec(statement).all()
        return [record_to_schema(PlannerOperation, record) for record in records]

    def _list_by_approval_state(
        self,
        approval_state: PlannerOperationApprovalState,
        *,
        session_id: str | None = None,
    ) -> list[PlannerOperation]:
        statement = (
            select(PlannerOperationRecord)
            .where(PlannerOperationRecord.approval_state == approval_state)
            .order_by(asc(PlannerOperationRecord.created_at))
        )
        if session_id is not None:
            statement = statement.where(PlannerOperationRecord.session_id == session_id)
        records = self._session.exec(statement).all()
        return [record_to_schema(PlannerOperation, record) for record in records]

    def _mark(
        self,
        operation_id: UUID,
        *,
        approval_state: PlannerOperationApprovalState,
        approved_at: datetime | None = None,
        committed_at: datetime | None = None,
        error_message: str | None = None,
    ) -> PlannerOperation | None:
        record = self._session.get(PlannerOperationRecord, operation_id)
        if record is None:
            return None
        record.approval_state = approval_state
        if approved_at is not None:
            record.approved_at = approved_at
        if committed_at is not None:
            record.committed_at = committed_at
        record.error_message = error_message
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(PlannerOperation, record)
