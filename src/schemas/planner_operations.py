"""Pending planner state-transition records.

PlannerOperation is not a first-class research object. It is the durable,
reviewable mutation envelope that commit applies to FCO records.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from schemas.common import CogniEDABaseModel, NonEmptyStr, utc_now
from schemas.enums import (
    PlannerNodeName,
    PlannerOperationApprovalState,
    PlannerOperationType,
)


class PlannerOperation(CogniEDABaseModel):
    """Durable pending mutation produced by a planner node."""

    operation_id: UUID = Field(default_factory=uuid4)
    session_id: NonEmptyStr | None = None
    operation_type: PlannerOperationType
    target_object_id: UUID | None = None
    target_object_type: NonEmptyStr | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    produced_by_node: PlannerNodeName
    requires_user_approval: bool = True
    approval_state: PlannerOperationApprovalState = PlannerOperationApprovalState.PENDING
    created_at: datetime = Field(default_factory=utc_now)
    approved_at: datetime | None = None
    committed_at: datetime | None = None
    error_message: str | None = None

    @model_validator(mode="after")
    def _approval_state_matches_user_approval_requirement(self) -> PlannerOperation:
        if self.requires_user_approval is False and self.approval_state == (
            PlannerOperationApprovalState.PENDING
        ):
            self.approval_state = PlannerOperationApprovalState.NOT_REQUIRED
        if self.requires_user_approval and self.approval_state == (
            PlannerOperationApprovalState.NOT_REQUIRED
        ):
            raise ValueError("User-governed PlannerOperations cannot be not_required.")
        return self


class PlannerCommitResult(CogniEDABaseModel):
    """Structured result returned by the PlannerOperation commit boundary."""

    committed_operation_ids: list[UUID] = Field(default_factory=list)
    failed_operation_ids: list[UUID] = Field(default_factory=list)
    skipped_operation_ids: list[UUID] = Field(default_factory=list)
    error_details: dict[UUID, str] = Field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        """Return whether the requested commit batch completed without failures."""

        return not self.failed_operation_ids and not self.error_details
