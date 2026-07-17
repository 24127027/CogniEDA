"""Pending planner state-transition records.

PlannerOperation is not a first-class research object. It is the durable,
reviewable mutation envelope that commit applies to FCO records.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from schemas.common import CogniEDABaseModel, NonEmptyStr, utc_now
from schemas.enums import (
    AssumptionStatus,
    ObjectiveStatus,
    PlannerNodeName,
    PlannerOperationApprovalState,
    PlannerOperationType,
    TaskKind,
    TaskLifecycleState,
)


class TaskCreateOperationPayload(BaseModel):
    """Typed persisted payload for creating one Task after user approval."""

    model_config = ConfigDict(extra="forbid")

    # Planner drafts deliberately omit this id; commit assigns it when it
    # materializes the durable Task. Existing reviewed operations may supply it.
    task_id: UUID | None = None
    title: NonEmptyStr
    description: NonEmptyStr
    lifecycle_state: TaskLifecycleState = TaskLifecycleState.ACTIVE
    task_kind: TaskKind = TaskKind.ANALYTICAL
    parent_task_id: UUID | None = None
    profile_id: UUID | None = None
    variables: list[NonEmptyStr] = Field(default_factory=list)
    evidence_expectation: str | None = None


class TaskUpdateOperationPayload(BaseModel):
    """Typed persisted payload for updating one Task."""

    model_config = ConfigDict(extra="forbid")

    task_id: UUID
    title: str | None = None
    description: str | None = None
    lifecycle_state: TaskLifecycleState | None = None
    task_kind: TaskKind | None = None
    parent_task_id: UUID | None = None
    profile_id: UUID | None = None
    variables: list[str] | None = None
    evidence_expectation: str | None = None


class TaskStateChangeOperationPayload(BaseModel):
    """Typed persisted payload for one Task lifecycle transition."""

    model_config = ConfigDict(extra="forbid")

    task_id: UUID
    lifecycle_state: TaskLifecycleState


class ObjectiveUpdateOperationPayload(BaseModel):
    """Typed persisted payload for updating one Objective."""

    model_config = ConfigDict(extra="forbid")

    objective_id: UUID
    title: str | None = None
    statement: str | None = None
    status: ObjectiveStatus | None = None


class AssumptionStateUpdateOperationPayload(BaseModel):
    """Typed persisted payload for updating one Assumption lifecycle state."""

    model_config = ConfigDict(extra="forbid")

    assumption_id: UUID
    status: AssumptionStatus | None = None
    contradicted_by_discovery_ids: list[UUID] | None = None
    replacement_assumption_id: UUID | None = None


class ConflictFlagOperationPayload(BaseModel):
    """Typed persisted payload for an Assumption review flag."""

    model_config = ConfigDict(extra="forbid")

    assumption_id: UUID
    target_object_type: str = "assumption"
    discovery_id: UUID | None = None
    contradicted_by_discovery_id: UUID | None = None
    reason: str | None = None


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
