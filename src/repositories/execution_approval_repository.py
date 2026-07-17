"""Persistence access for durable execution-approval records."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session, select

from db.models import ExecutionApprovalRecord
from repositories.common import record_to_schema, schema_to_record_payload
from schemas.enums import ExecutionApprovalStatus
from schemas.provenance import ExecutionApproval


class ExecutionApprovalRepository:
    """Store and transition one session-bound execution approval at a time."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, approval: ExecutionApproval) -> ExecutionApproval:
        record = ExecutionApprovalRecord(**schema_to_record_payload(approval))
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(ExecutionApproval, record)

    def get_by_id(self, approval_id: UUID) -> ExecutionApproval | None:
        record = self._session.get(ExecutionApprovalRecord, approval_id)
        return record_to_schema(ExecutionApproval, record) if record is not None else None

    def find_pending(
        self,
        *,
        session_id: str,
        task_id: UUID,
        contract_fingerprint: str,
    ) -> ExecutionApproval | None:
        record = self._session.exec(
            select(ExecutionApprovalRecord).where(
                ExecutionApprovalRecord.session_id == session_id,
                ExecutionApprovalRecord.task_id == task_id,
                ExecutionApprovalRecord.contract_fingerprint == contract_fingerprint,
                ExecutionApprovalRecord.status == ExecutionApprovalStatus.PENDING,
            )
        ).first()
        return record_to_schema(ExecutionApproval, record) if record is not None else None

    def set_status(
        self,
        approval_id: UUID,
        *,
        expected_status: ExecutionApprovalStatus,
        status: ExecutionApprovalStatus,
        execution_run_id: UUID | None = None,
    ) -> ExecutionApproval:
        record = self._session.get(ExecutionApprovalRecord, approval_id)
        if record is None or record.status != expected_status:
            raise ValueError("Execution approval is unknown or no longer in the expected state.")
        record.status = status
        record.execution_run_id = execution_run_id
        record.updated_at = datetime.now(UTC)
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(ExecutionApproval, record)
