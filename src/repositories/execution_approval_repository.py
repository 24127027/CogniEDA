"""Persistence access for durable Planner execution approvals."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session, desc, select

from db.models import ExecutionApprovalRecord
from repositories.common import record_to_schema, schema_to_record_payload
from schemas.enums import ExecutionApprovalStatus
from schemas.provenance import ExecutionApproval

EXECUTION_APPROVAL_JSON_FIELDS = {"prepared_payload"}


class ExecutionApprovalRepository:
    """Repository for the approval boundary of one execution attempt."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, approval: ExecutionApproval) -> ExecutionApproval:
        record = self.stage_create(approval)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(ExecutionApproval, record)

    def stage_create(self, approval: ExecutionApproval) -> ExecutionApprovalRecord:
        record = ExecutionApprovalRecord(
            **schema_to_record_payload(approval, json_fields=EXECUTION_APPROVAL_JSON_FIELDS)
        )
        self._session.add(record)
        return record

    def get_by_id(self, approval_id: UUID) -> ExecutionApproval | None:
        record = self._session.get(ExecutionApprovalRecord, approval_id)
        return None if record is None else record_to_schema(ExecutionApproval, record)

    def find_pending(
        self,
        *,
        session_id: str,
        task_id: UUID,
        contract_fingerprint: str,
    ) -> ExecutionApproval | None:
        record = self._session.exec(
            select(ExecutionApprovalRecord)
            .where(ExecutionApprovalRecord.session_id == session_id)
            .where(ExecutionApprovalRecord.task_id == task_id)
            .where(ExecutionApprovalRecord.contract_fingerprint == contract_fingerprint)
            .where(ExecutionApprovalRecord.status == ExecutionApprovalStatus.PENDING)
            .order_by(desc(ExecutionApprovalRecord.created_at))
        ).first()
        return None if record is None else record_to_schema(ExecutionApproval, record)

    def set_status(
        self,
        approval_id: UUID,
        status: ExecutionApprovalStatus,
        *,
        execution_run_id: UUID | None = None,
    ) -> ExecutionApproval | None:
        record = self._session.get(ExecutionApprovalRecord, approval_id)
        if record is None:
            return None
        record.status = status
        if execution_run_id is not None:
            record.execution_run_id = execution_run_id
        record.updated_at = datetime.now(UTC)
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record_to_schema(ExecutionApproval, record)
