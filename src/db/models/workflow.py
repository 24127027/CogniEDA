"""SQLModel table definitions for workflow-owned records."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from db.models.common import utc_now
from schemas.enums import (
    PlannerNodeName,
    PlannerOperationApprovalState,
    PlannerOperationType,
)


class PlannerOperationRecord(SQLModel, table=True):
    """Persisted pending mutation produced by planner nodes."""

    __tablename__ = "planner_operations"

    operation_id: UUID = Field(default_factory=uuid4, primary_key=True)
    session_id: str | None = Field(default=None, index=True)
    operation_type: PlannerOperationType = Field(nullable=False, index=True)
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    produced_by_node: PlannerNodeName = Field(nullable=False, index=True)
    approval_state: PlannerOperationApprovalState = Field(
        default=PlannerOperationApprovalState.PENDING,
        nullable=False,
        index=True,
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)
    committed_at: datetime | None = Field(default=None, nullable=True)
