"""Planner-specific graph contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Literal, Protocol, runtime_checkable
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_ai.messages import ModelMessage

from schemas.artifacts import Assumption
from schemas.common import NonEmptyStr
from schemas.enums import AssumptionStatus, ObjectiveStatus, TaskKind, TaskLifecycleState
from schemas.planner_operations import (
    PlannerCommitResult,
    PlannerOperation,
    TaskCreateOperationPayload,
)

PlannerIntent = Literal[
    "answer",
    "suggest",
    "manage_task",
    "decompose",
    "execute",
    "objective",
    "assumption",
]

COMMAND_TO_INTENT: dict[str, PlannerIntent] = {
    "answer": "answer",
    "suggest": "suggest",
    "manage_task": "manage_task",
    "decompose": "decompose",
    "execute": "execute",
    "objective": "objective",
    "assumption": "assumption",
}


class ExplicitCommandParseResult(BaseModel):
    """The command token and payload parsed from a raw planner request."""

    command: str
    original_command: str
    request_text: str


def parse_explicit_command(query: str) -> ExplicitCommandParseResult | None:
    """Parse a leading slash command without interpreting ordinary request text."""

    stripped_query = query.lstrip()
    if not stripped_query.startswith("/"):
        return None
    tokens = stripped_query.split(maxsplit=1)
    command_token = tokens[0]
    return ExplicitCommandParseResult(
        command=command_token[1:].lower(),
        original_command=command_token,
        request_text=tokens[1].strip() if len(tokens) == 2 else "",
    )


class RequestUnderstanding(BaseModel):
    """Transient classification of the latest planner request."""

    intent: PlannerIntent | None
    request_text: str
    source: Literal["explicit_command", "llm", "invalid_command", "invalid_llm"]
    explicit_command: str | None = None
    requires_user_correction: bool = False
    error_message: str | None = None
    supported_commands: tuple[str, ...] = ()


class RequestUnderstandingModel(ABC):
    """Injectable structured model used only to classify the latest request."""

    @abstractmethod
    def understand(self, prompt: str) -> RequestUnderstanding:
        """Return a structured classification for the supplied request-only prompt."""


@runtime_checkable
class TaskManagementModel(Protocol):
    """Dependency that produces typed draft data for /manage_task."""

    def draft(self, prompt: str) -> Any: ...


@runtime_checkable
class TaskDecompositionModel(Protocol):
    """Dependency that proposes bounded, non-executable child Tasks."""

    def draft(self, prompt: str) -> Any: ...


class TaskCreateDraft(BaseModel):
    """Planner-owned draft for a Task-create operation."""

    model_config = ConfigDict(extra="forbid")

    title: NonEmptyStr
    description: NonEmptyStr
    lifecycle_state: TaskLifecycleState = TaskLifecycleState.ACTIVE
    task_kind: TaskKind = TaskKind.ANALYTICAL
    variables: list[NonEmptyStr] = Field(default_factory=list)
    evidence_expectation: str | None = None

    def operation_payload(self) -> TaskCreateOperationPayload:
        """Serialize the reviewed draft at the PlannerOperation boundary."""

        return TaskCreateOperationPayload(**self.model_dump(mode="python"))


class ChildTaskProposalDraft(BaseModel):
    """One non-executable child Task proposed by ``/decompose``."""

    model_config = ConfigDict(extra="forbid")

    title: NonEmptyStr
    description: NonEmptyStr
    task_kind: Literal[TaskKind.ORGANIZING, TaskKind.REVIEW] = TaskKind.ORGANIZING

    def operation_payload(self, *, parent_task_id: UUID) -> TaskCreateOperationPayload:
        """Create a payload that cannot be admitted to analytical execution."""

        return TaskCreateOperationPayload(
            title=self.title,
            description=self.description,
            lifecycle_state=TaskLifecycleState.PROPOSED,
            task_kind=self.task_kind,
            parent_task_id=parent_task_id,
        )


class TaskDecompositionDraft(BaseModel):
    """Typed child-Task proposal returned by the bounded decomposition model."""

    model_config = ConfigDict(extra="forbid")

    child_task_proposals: list[ChildTaskProposalDraft] = Field(min_length=1, max_length=8)


class _TargetedOperationDraft(BaseModel):
    """Shared target id handling for planner operation drafts."""

    model_config = ConfigDict(extra="forbid")

    target_object_id: UUID | None = None

    def require_target_object_id(self) -> UUID:
        """Return the target object id or fail before a PlannerOperation is created."""

        if self.target_object_id is None:
            raise ValueError("Planner operation draft requires target_object_id.")
        return self.target_object_id


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

    def operation_payload(self) -> dict[str, object]:
        """Serialize only update fields for PlannerOperation.payload."""

        return self.model_dump(
            mode="json",
            exclude={"task_id", "target_object_id"},
            exclude_unset=True,
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

    def operation_payload(self) -> dict[str, object]:
        """Serialize the lifecycle transition for PlannerOperation.payload."""

        return self.model_dump(
            mode="json",
            exclude={"task_id", "target_object_id"},
        )


class ObjectiveUpdateDraft(_TargetedOperationDraft):
    """Typed planner draft for Objective updates."""

    objective_id: UUID | None = None
    title: str | None = None
    statement: str | None = None
    status: ObjectiveStatus | None = None

    @model_validator(mode="after")
    def _resolve_target_alias(self) -> ObjectiveUpdateDraft:
        if self.target_object_id is None:
            self.target_object_id = self.objective_id
        if self.target_object_id is None:
            raise ValueError("ObjectiveUpdateDraft requires objective_id or target_object_id.")
        return self

    def operation_payload(self) -> dict[str, object]:
        """Serialize Objective update fields for PlannerOperation.payload."""

        return self.model_dump(
            mode="json",
            exclude={"objective_id", "target_object_id"},
            exclude_unset=True,
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

    def operation_payload(self) -> dict[str, object]:
        """Serialize Assumption update fields for PlannerOperation.payload."""

        return self.model_dump(
            mode="json",
            exclude={"assumption_id", "target_object_id"},
            exclude_unset=True,
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

    def operation_payload(self) -> dict[str, object]:
        """Serialize flag metadata for PlannerOperation.payload."""

        return self.model_dump(
            mode="json",
            exclude={"assumption_id", "target_object_id", "target_object_type"},
            exclude_none=True,
        )


class PendingUserInteraction(BaseModel):
    """JSON-safe description of the exact operation batch awaiting approval."""

    kind: Literal["planner_operation_approval"]
    payload: dict[str, Any] = Field(default_factory=dict)
    allowed_actions: list[str]
    operation_ids: list[str] = Field(default_factory=list)
    snapshot_hash: str
    proposal_id: str


class PlannerDecision(BaseModel):
    """One normalized user response for a pending Planner interaction."""

    action: Literal["approve", "cancel", "revise", "clarify"]
    selected_ids: list[str] = Field(default_factory=list)
    feedback: str | None = None
    proposal_id: str | None = None


class ControlledPlannerError(BaseModel):
    """User-visible failure that does not expose internal object handles."""

    code: str
    message: str


class State(BaseModel):
    """Internal Planner state."""

    query: str
    request_understanding: RequestUnderstanding | None = None
    planner_decision: PlannerDecision | None = None
    resume_requested: bool = False
    resume_operation_ids: list[UUID] = Field(default_factory=list)
    pending_interaction: PendingUserInteraction | None = None
    controlled_error: ControlledPlannerError | None = None
    interaction_error: str | None = None
    session_id: str | None = None
    history: list[ModelMessage] = Field(default_factory=list)
    task_create_payloads: list[TaskCreateDraft] = Field(default_factory=list)
    task_decomposition_payloads: list[TaskDecompositionDraft] = Field(default_factory=list)
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

    model_config = ConfigDict(arbitrary_types_allowed=True)

    database_url: str | None = None
    session_id: str | None = None
    request_understanding_model: RequestUnderstandingModel | None = None
    task_management_model: TaskManagementModel | None = None
    task_decomposition_model: TaskDecompositionModel | None = None


class PlannerOutput(BaseModel):
    """PydanticAI output schema for planner-authored requests."""

    pending_interaction: PendingUserInteraction | None = None
    controlled_error: ControlledPlannerError | None = None
    committed_operation_ids: list[UUID] = Field(default_factory=list)
    planner_operations: list[PlannerOperation] = Field(default_factory=list)
    commit_result: PlannerCommitResult | None = None


