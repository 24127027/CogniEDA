"""Pending planner state-transition records.

PlannerOperation is not a first-class research object. It is the durable,
reviewable mutation envelope that commit applies to FCO records.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

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


class TaskUpdateOperationPayload(BaseModel):
    """Persisted Task update payload; UUIDs exist only at the commit boundary."""

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
    """Persisted Task lifecycle payload."""

    model_config = ConfigDict(extra="forbid")

    task_id: UUID
    lifecycle_state: TaskLifecycleState


class ObjectiveUpdateOperationPayload(BaseModel):
    """Persisted Objective update payload."""

    model_config = ConfigDict(extra="forbid")

    objective_id: UUID
    title: str | None = None
    statement: str | None = None
    status: ObjectiveStatus | None = None
    revision_reason: str | None = None
    user_decision_id: str | None = None
    created_by: str | None = None


class AssumptionStateUpdateOperationPayload(BaseModel):
    """Persisted Assumption lifecycle payload."""

    model_config = ConfigDict(extra="forbid")

    assumption_id: UUID
    status: AssumptionStatus | None = None
    contradicted_by_discovery_ids: list[UUID] | None = None
    replacement_assumption_id: UUID | None = None


class ConflictFlagOperationPayload(BaseModel):
    """Persisted conflict-review payload."""

    model_config = ConfigDict(extra="forbid")

    assumption_id: UUID
    target_object_type: str = "assumption"
    discovery_id: UUID | None = None
    contradicted_by_discovery_id: UUID | None = None
    reason: str | None = None


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
