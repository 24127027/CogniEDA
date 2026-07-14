"""Persistence access for minimal ExecutionOutbox records."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, desc, select

from db.models import ExecutionOutboxRecord
from repositories.common import record_to_schema
from schemas.provenance import ExecutionOutbox


class ExecutionOutboxRepository:
    """Repository for execution outbox records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, outbox_id: UUID) -> ExecutionOutbox | None:
        """Return an ExecutionOutbox by primary id if it exists."""
        record = self._session.get(ExecutionOutboxRecord, outbox_id)
        if record is None:
            return None
        return record_to_schema(ExecutionOutbox, record)

    def list(
        self,
        *,
        execution_run_id: UUID | None = None,
        dispatch_idempotency_key: str | None = None,
        status: str | None = None,
    ) -> list[ExecutionOutbox]:
        """List ExecutionOutbox records with simple filters."""
        statement = select(ExecutionOutboxRecord).order_by(desc(ExecutionOutboxRecord.created_at))
        if execution_run_id is not None:
            statement = statement.where(ExecutionOutboxRecord.execution_run_id == execution_run_id)
        if dispatch_idempotency_key is not None:
            statement = statement.where(
                ExecutionOutboxRecord.dispatch_idempotency_key == dispatch_idempotency_key
            )
        if status is not None:
            statement = statement.where(ExecutionOutboxRecord.status == status)
        records = self._session.exec(statement).all()
        return [record_to_schema(ExecutionOutbox, record) for record in records]
