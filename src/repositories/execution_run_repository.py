"""Persistence access for ExecutionRun provenance and dispatch leases."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, desc, select

from db.models import ExecutionRunRecord
from repositories.common import record_to_schema
from schemas.provenance import ExecutionRun


class ExecutionRunRepository:
    """Repository for provenance-only ExecutionRun records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, execution_run_id: UUID) -> ExecutionRun | None:
        """Return an ExecutionRun by primary id if it exists."""

        record = self._session.get(ExecutionRunRecord, execution_run_id)
        if record is None:
            return None
        return record_to_schema(ExecutionRun, record)

    def list(
        self,
        *,
        task_id: UUID | None = None,
        hypothesis_id: UUID | None = None,
        status: str | None = None,
    ) -> list[ExecutionRun]:
        """List ExecutionRun records with simple provenance filters."""

        statement = select(ExecutionRunRecord).order_by(desc(ExecutionRunRecord.created_at))
        if task_id is not None:
            statement = statement.where(ExecutionRunRecord.task_id == task_id)
        if hypothesis_id is not None:
            statement = statement.where(ExecutionRunRecord.hypothesis_id == hypothesis_id)
        if status is not None:
            statement = statement.where(ExecutionRunRecord.status == status)
        records = self._session.exec(statement).all()
        return [record_to_schema(ExecutionRun, record) for record in records]
