"""Planner-specific graph contracts."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_ai.messages import ModelMessage
from schemas.artifacts import Assumption, Task
from schemas.enums import AssumptionStatus, ObjectiveStatus, TaskKind, TaskLifecycleState
from schemas.planner_operations import PlannerCommitResult, PlannerOperation


class _TargetedOperationDraft(BaseModel):
    """Shared target id handling for planner operation drafts."""

    model_config = ConfigDict(extra="forbid")

    target_object_id: UUID | None = None

    def require_target_object_id(self) -> UUID:
        """Return the target object id or fail before a PlannerOperation is created."""

        if self.target_object_id is None:
            raise ValueError("Planner operation draft requires target_object_id.")
        return self.target_object_id


class TaskUpdateOperationPayload(BaseModel):
    """Explicit PlannerOperation payload for Task field updates."""

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
    """Explicit PlannerOperation payload for Task lifecycle changes."""

    model_config = ConfigDict(extra="forbid")

    task_id: UUID
    lifecycle_state: TaskLifecycleState


class ObjectiveUpdateOperationPayload(BaseModel):
    """Explicit PlannerOperation payload for Objective updates."""

    model_config = ConfigDict(extra="forbid")

    objective_id: UUID
    title: str | None = None
    statement: str | None = None
    status: ObjectiveStatus | None = None
    revision_reason: str | None = None
    user_decision_id: str | None = None
    created_by: str | None = None


class AssumptionStateUpdateOperationPayload(BaseModel):
    """Explicit PlannerOperation payload for Assumption lifecycle updates."""

    model_config = ConfigDict(extra="forbid")

    assumption_id: UUID
    status: AssumptionStatus | None = None
    contradicted_by_discovery_ids: list[UUID] | None = None
    replacement_assumption_id: UUID | None = None


class ConflictFlagOperationPayload(BaseModel):
    """Explicit PlannerOperation payload for user-review conflict flags."""

    model_config = ConfigDict(extra="forbid")

    assumption_id: UUID
    target_object_type: str = "assumption"
    discovery_id: UUID | None = None
    contradicted_by_discovery_id: UUID | None = None
    reason: str | None = None


class TaskUpdateDraft(_TargetedOperationDraft):
    """Typed planner draft for Task field updates."""

    task_id: UUID | None = None
    title: str | None = None
    description: str | None = None
    lifecycle_state: TaskLifecycleState | None = None
    task_kind: TaskKind | None = None
    parent_task_id: UUID | None = None
    profile_id: UUID | None = None
    variables: list[str] | None = None
    evidence_expectation: str | None = None

    @model_validator(mode="after")
    def _resolve_target_alias(self) -> TaskUpdateDraft:
        if self.target_object_id is None:
            self.target_object_id = self.task_id
        if self.target_object_id is None:
            raise ValueError("TaskUpdateDraft requires task_id or target_object_id.")
        return self

    def operation_payload(self) -> TaskUpdateOperationPayload:
        """Return the typed operation payload for this Task update."""

        payload = self.model_dump(
            mode="python",
            exclude={"task_id", "target_object_id"},
            exclude_unset=True,
        )
        return TaskUpdateOperationPayload(
            task_id=self.require_target_object_id(),
            **payload,
        )


class TaskStateChangeDraft(_TargetedOperationDraft):
    """Typed planner draft for Task lifecycle changes."""

    task_id: UUID | None = None
    lifecycle_state: TaskLifecycleState

    @model_validator(mode="after")
    def _resolve_target_alias(self) -> TaskStateChangeDraft:
        if self.target_object_id is None:
            self.target_object_id = self.task_id
        if self.target_object_id is None:
            raise ValueError("TaskStateChangeDraft requires task_id or target_object_id.")
        return self

    def operation_payload(self) -> TaskStateChangeOperationPayload:
        """Return the typed operation payload for this Task state change."""

        payload = self.model_dump(
            mode="python",
            exclude={"task_id", "target_object_id"},
        )
        return TaskStateChangeOperationPayload(
            task_id=self.require_target_object_id(),
            **payload,
        )


class ObjectiveUpdateDraft(_TargetedOperationDraft):
    """Typed planner draft for Objective updates."""

    objective_id: UUID | None = None
    title: str | None = None
    statement: str | None = None
    status: ObjectiveStatus | None = None
    revision_reason: str | None = None
    user_decision_id: str | None = None
    created_by: str | None = None

    @model_validator(mode="after")
    def _resolve_target_alias(self) -> ObjectiveUpdateDraft:
        if self.target_object_id is None:
            self.target_object_id = self.objective_id
        if self.target_object_id is None:
            raise ValueError("ObjectiveUpdateDraft requires objective_id or target_object_id.")
        return self

    def operation_payload(self) -> ObjectiveUpdateOperationPayload:
        """Return the typed operation payload for this Objective update."""

        payload = self.model_dump(
            mode="python",
            exclude={"objective_id", "target_object_id"},
            exclude_unset=True,
        )
        return ObjectiveUpdateOperationPayload(
            objective_id=self.require_target_object_id(),
            **payload,
        )


class AssumptionStateUpdateDraft(_TargetedOperationDraft):
    """Typed planner draft for Assumption lifecycle review updates."""

    assumption_id: UUID | None = None
    status: AssumptionStatus | None = None
    contradicted_by_discovery_ids: list[UUID] | None = None
    replacement_assumption_id: UUID | None = None

    @model_validator(mode="after")
    def _resolve_target_alias(self) -> AssumptionStateUpdateDraft:
        if self.target_object_id is None:
            self.target_object_id = self.assumption_id
        if self.target_object_id is None:
            raise ValueError(
                "AssumptionStateUpdateDraft requires assumption_id or target_object_id."
            )
        return self

    def operation_payload(self) -> AssumptionStateUpdateOperationPayload:
        """Return the typed operation payload for this Assumption update."""

        payload = self.model_dump(
            mode="python",
            exclude={"assumption_id", "target_object_id"},
            exclude_unset=True,
        )
        return AssumptionStateUpdateOperationPayload(
            assumption_id=self.require_target_object_id(),
            **payload,
        )


class ConflictFlagDraft(_TargetedOperationDraft):
    """Typed planner draft for flagging an object for user review."""

    assumption_id: UUID | None = None
    target_object_type: str = "assumption"
    discovery_id: UUID | None = None
    contradicted_by_discovery_id: UUID | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def _resolve_target_alias(self) -> ConflictFlagDraft:
        if self.target_object_id is None:
            self.target_object_id = self.assumption_id
        if self.target_object_id is None:
            raise ValueError("ConflictFlagDraft requires assumption_id or target_object_id.")
        return self

    def operation_payload(self) -> ConflictFlagOperationPayload:
        """Return the typed operation payload for this conflict flag."""

        payload = self.model_dump(
            mode="python",
            exclude={"assumption_id", "target_object_id"},
            exclude_none=True,
        )
        return ConflictFlagOperationPayload(
            assumption_id=self.require_target_object_id(),
            **payload,
        )


class State(BaseModel):
    """Internal Planner state."""

    query: str
    session_id: str | None = None
    history: list[ModelMessage] = Field(default_factory=list)
    task_create_payloads: list[Task] = Field(default_factory=list)
    task_update_payloads: list[TaskUpdateDraft] = Field(default_factory=list)
    task_state_change_payloads: list[TaskStateChangeDraft] = Field(default_factory=list)
    objective_update_payloads: list[ObjectiveUpdateDraft] = Field(default_factory=list)
    assumption_create_payloads: list[Assumption] = Field(default_factory=list)
    assumption_state_update_payloads: list[AssumptionStateUpdateDraft] = Field(
        default_factory=list
    )
    conflict_flag_payloads: list[ConflictFlagDraft] = Field(default_factory=list)
    planner_operations: list[PlannerOperation] = Field(default_factory=list)
    operation_ids_to_commit: list[UUID] | None = None
    commit_result: PlannerCommitResult | None = None


class Context(BaseModel):
    """Context for the Planner agent."""

    database_url: str | None = None
    session_id: str | None = None


class PlannerOutput(BaseModel):
    """Planner payload contract returned to the runtime."""

    planner_operations: list[PlannerOperation] = Field(default_factory=list)
    executor_dispatch_ref: str | None = None
    commit_result: PlannerCommitResult | None = None
