"""Pending planner state-transition records.

PlannerOperation is not a first-class research object. It is the durable,
reviewable mutation envelope that commit applies to FCO records.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field
from schemas.common import CogniEDABaseModel, NonEmptyStr, utc_now
from schemas.enums import (
    PlannerNodeName,
    PlannerOperationApprovalState,
    PlannerOperationType,
)


class PlannerOperation(CogniEDABaseModel):
    """Minimal pending mutation envelope produced by a planner node."""

    operation_id: UUID = Field(default_factory=uuid4)
    session_id: NonEmptyStr | None = None
    operation_type: PlannerOperationType
    payload: dict[str, Any] = Field(default_factory=dict)
    approval_state: PlannerOperationApprovalState = PlannerOperationApprovalState.PENDING
    produced_by_node: PlannerNodeName
    created_at: datetime = Field(default_factory=utc_now)
    committed_at: datetime | None = None


class PlannerCommitResult(CogniEDABaseModel):
    """Structured result returned by the PlannerOperation commit boundary."""

    committed_operation_ids: list[UUID] = Field(default_factory=list)
    skipped_operation_ids: list[UUID] = Field(default_factory=list)
    failed_operation_ids: list[UUID] = Field(default_factory=list)
    message: str | None = None
    errors: dict[UUID, str] = Field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        """Return whether the requested commit batch completed without failures."""

        return not self.failed_operation_ids and not self.errors
