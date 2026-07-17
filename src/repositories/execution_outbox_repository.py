"""Read access for durable execution dispatch intents."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, desc, select

from db.models import ExecutionOutboxRecord
from repositories.common import record_to_schema
from schemas.provenance import ExecutionOutbox


class ExecutionOutboxRepository:
    """Repository for durable outbox records owned by the transition service."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_execution_run_id(self, execution_run_id: UUID) -> ExecutionOutbox | None:
        record = self._session.exec(
            select(ExecutionOutboxRecord).where(
                ExecutionOutboxRecord.execution_run_id == execution_run_id
            )
        ).first()
        return record_to_schema(ExecutionOutbox, record) if record is not None else None

    def list(self, *, execution_run_id: UUID | None = None) -> list[ExecutionOutbox]:
        statement = select(ExecutionOutboxRecord).order_by(desc(ExecutionOutboxRecord.created_at))
        if execution_run_id is not None:
            statement = statement.where(ExecutionOutboxRecord.execution_run_id == execution_run_id)
        return [
            record_to_schema(ExecutionOutbox, record)
            for record in self._session.exec(statement).all()
        ]
