"""Planner-specific graph contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from secrets import token_urlsafe
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_ai.messages import ModelMessage

from schemas.artifacts import Assumption, EvaluationThresholds, Task
from schemas.common import EvidenceResultSummary, MethodParameter
from schemas.enums import (
    AssumptionStatus,
    EvidenceType,
    HypothesisEvidenceOutcome,
    HypothesisStatus,
    ObjectiveStatus,
    PlannerCapability,
    TaskKind,
    TaskLifecycleState,
)
from schemas.planner_operations import (
    AssumptionStateUpdateOperationPayload,
    ConflictFlagOperationPayload,
    ObjectiveUpdateOperationPayload,
    PlannerCommitResult,
    PlannerOperation,
    TaskStateChangeOperationPayload,
    TaskUpdateOperationPayload,
)

PlannerIntent = Literal[
    "answer",
    "suggest",
    "manage_task",
    "execute",
    "objective",
    "register_dataset",
    "assumption",
    "close_project",
    "profile",
    "review_profile",
    "clean",
    "accept_profile",
    "review_result",
    "review_conflict",
]
PendingInteractionKind = Literal[
    "research_direction_approval",
    "planner_operation_approval",
    "execution_approval",
    "execution_failure_review",
]


class GovernanceMode(StrEnum):
    """Small, explicit control setting for planner confirmation gates."""

    ALWAYS_ASK = "always_ask"
    RISK_BASED = "risk_based"
    FULL_AUTONOMY = "full_autonomy"


COMMAND_TO_INTENT: dict[str, PlannerIntent] = {
    "answer": "answer",
    "suggest": "suggest",
    "manage_task": "manage_task",
    "execute": "execute",
    "objective": "objective",
    "register_dataset": "register_dataset",
    "assumption": "assumption",
    "close_project": "close_project",
    "profile": "profile",
    "review_profile": "review_profile",
    "clean": "clean",
    "accept_profile": "accept_profile",
    "review_result": "review_result",
    "review_conflict": "review_conflict",
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
    payload = tokens[1] if len(tokens) == 2 else ""

    return ExplicitCommandParseResult(
        command=command_token[1:].lower(),
        original_command=command_token,
        request_text=payload.strip(),
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


def new_local_reference(object_type: str) -> str:
    """Create a graph-local handle that agents may exchange without durable UUIDs."""

    return f"{object_type}:{token_urlsafe(9)}"


class TaskSelection(BaseModel):
    """Transient, deterministic result of resolving one execution Task reference."""

    task_ref: str | None = None
    selected: bool = False
    error_code: str | None = None
    error_message: str | None = None


class HypothesisDraft(BaseModel):
    """Transient hypothesis contract without a durable Hypothesis identity."""

    statement: str
    variables: list[str] = Field(default_factory=list)
    scope: str
    validation_method: str
    evidence_expectation: str


class ExecutionSpecification(BaseModel):
    """Executor-facing analytical method contract without persistent FCO references."""

    claim_type: Literal["association"]
    variable_bindings: list[str] = Field(default_factory=list)
    scope: str
    evidence_expectation: str
    decision_rule: EvaluationThresholds
    validation_method: str
    executor_id: str
    method_parameters: list[MethodParameter] = Field(default_factory=list)


class PreparedExecution(BaseModel):
    """Typed executor contract reconstructed from durable admission state.

    Local references help only while the Planner prepares approval.  Once
    admitted, the dispatcher supplies the durable attempt identity below, so
    executors do not need Planner graph state to run the contract.
    """

    execution_ref: str = Field(default_factory=lambda: new_local_reference("execution"))
    task_ref: str
    data_profile_ref: str
    hypothesis_ref: str | None = None
    execution_run_ref: str | None = None
    task_title: str
    dataset_path: str
    hypothesis: HypothesisDraft
    specification: ExecutionSpecification
    deterministic_seed: int | None = None
    contract_fingerprint: str
    execution_run_id: UUID | None = None
    dispatch_idempotency_key: str | None = None
    lease_epoch: int | None = None


class PendingUserInteraction(BaseModel):
    """JSON-safe description of one planner interaction that must be resumed."""

    kind: PendingInteractionKind
    payload: dict[str, Any] = Field(default_factory=dict)
    allowed_actions: list[str]
    operation_ids: list[str] = Field(default_factory=list)
    snapshot_hash: str | None = None
    proposal_id: str | None = None


class PlannerDecision(BaseModel):
    """One normalized, transient answer to a pending planner interaction."""

    action: Literal["approve", "cancel", "revise", "clarify"]
    selected_ids: list[str] = Field(default_factory=list)
    feedback: str | None = None
    execution_ref: str | None = None
    proposal_id: str | None = None


class ExecutionAdmission(BaseModel):
    """Transient references returned after the database admits an execution."""

    admitted: bool = False
    hypothesis_ref: str | None = None
    execution_run_ref: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class ExecutionRevalidation(BaseModel):
    """Deterministic result of checking an approved contract after an interrupt."""

    valid: bool = False
    error_code: str | None = None
    error_message: str | None = None


class AuthorizationResult(BaseModel):
    """Small local result from one approval boundary."""

    approved: bool = False
    terminated: bool = False
    error_message: str | None = None


class AnalysisFrameObservation(BaseModel):
    """Executor-provided analysis-view facts before provenance is materialized."""

    frame_hash: str | None = None
    frame_ref: str | None = None
    column_refs: list[str] = Field(default_factory=list)
    row_filter_description: str | None = None

    @model_validator(mode="after")
    def _has_frame_identity(self) -> AnalysisFrameObservation:
        if self.frame_hash is None and self.frame_ref is None:
            raise ValueError("Analysis frame observation requires frame_hash or frame_ref.")
        return self


class ExecutionRunObservation(BaseModel):
    """Executor-provided run facts before durable provenance is materialized."""

    executor_type: str | None = None
    method_id: str | None = None
    parameter_hash: str | None = None
    status: str = "pending"


class EvidenceObservation(BaseModel):
    """Observed result returned by an executor before Evidence is authored at review."""

    evidence_type: EvidenceType
    method: str
    parameters: list[MethodParameter] = Field(default_factory=list)
    result_summary: EvidenceResultSummary
    artifact_refs: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    code_reference: str | None = None
    environment_reference: str | None = None


class HypothesisEvaluationDraft(BaseModel):
    """Executor evaluation linked to the current local execution rather than a UUID."""

    outcome: HypothesisEvidenceOutcome
    note: str | None = None
    finalize: bool = False


class ExecutorResult(BaseModel):
    """Typed executor outcome; failures cannot carry observed Evidence."""

    status: Literal["completed", "failed"]
    analysis_frame: AnalysisFrameObservation
    execution_run: ExecutionRunObservation
    evidence_observation: EvidenceObservation | None = None
    evaluation: HypothesisEvaluationDraft | None = None
    error_message: str | None = None

    @model_validator(mode="after")
    def _validate_completed_result(self) -> ExecutorResult:
        if self.execution_run.status != self.status:
            raise ValueError(
                "Executor result status must match its ExecutionRun observation status."
            )
        if self.status == "completed" and (
            self.evidence_observation is None or self.evaluation is None
        ):
            raise ValueError("Completed executor results require Evidence and evaluation.")
        if self.status == "failed":
            if self.evidence_observation is not None:
                raise ValueError("Failed executor results must not carry observed Evidence.")
            if not self.error_message:
                raise ValueError("Failed executor results require failure information.")
        return self


class ExecutionPreparation(BaseModel):
    """Controlled readiness result retained only in planner state."""

    prepared: bool = False
    error_code: str | None = None
    error_message: str | None = None


class ExecutionReviewResult(BaseModel):
    """Controlled outcome of reviewing executor output into mutation operations."""

    reviewed: bool = False
    succeeded: bool = False
    error_code: str | None = None
    error_message: str | None = None
    failure_kind: str | None = None


class TaskUpdateDraft(BaseModel):
    """Planner Task-update draft addressed by a graph-local Task reference."""

    model_config = ConfigDict(extra="forbid")

    task_ref: str
    title: str | None = None
    description: str | None = None
    lifecycle_state: TaskLifecycleState | None = None
    task_kind: TaskKind | None = None
    parent_task_ref: str | None = None
    data_profile_ref: str | None = None
    variables: list[str] | None = None
    evidence_expectation: str | None = None

    def operation_payload(
        self,
        *,
        task_id: UUID,
        parent_task_id: UUID | None = None,
        profile_id: UUID | None = None,
    ) -> TaskUpdateOperationPayload:
        """Return the typed operation payload for this Task update."""

        payload = self.model_dump(
            mode="python",
            exclude={"task_ref", "parent_task_ref", "data_profile_ref"},
            exclude_unset=True,
        )
        if "parent_task_ref" in self.model_fields_set:
            payload["parent_task_id"] = parent_task_id
        if "data_profile_ref" in self.model_fields_set:
            payload["profile_id"] = profile_id
        return TaskUpdateOperationPayload(
            task_id=task_id,
            **payload,
        )


class TaskStateChangeDraft(BaseModel):
    """Planner Task-state draft addressed by a graph-local Task reference."""

    model_config = ConfigDict(extra="forbid")

    task_ref: str
    lifecycle_state: TaskLifecycleState

    def operation_payload(self, *, task_id: UUID) -> TaskStateChangeOperationPayload:
        """Return the typed operation payload for this Task state change."""

        payload = self.model_dump(
            mode="python",
            exclude={"task_ref"},
        )
        return TaskStateChangeOperationPayload(
            task_id=task_id,
            **payload,
        )


class ObjectiveUpdateDraft(BaseModel):
    """Planner Objective-update draft addressed by a graph-local Objective reference."""

    model_config = ConfigDict(extra="forbid")

    objective_ref: str
    title: str | None = None
    statement: str | None = None
    status: ObjectiveStatus | None = None
    revision_reason: str | None = None
    user_decision_id: str | None = None
    created_by: str | None = None

    def operation_payload(self, *, objective_id: UUID) -> ObjectiveUpdateOperationPayload:
        """Return the typed operation payload for this Objective update."""

        payload = self.model_dump(
            mode="python",
            exclude={"objective_ref"},
            exclude_unset=True,
        )
        return ObjectiveUpdateOperationPayload(
            objective_id=objective_id,
            **payload,
        )


class AssumptionStateUpdateDraft(BaseModel):
    """Planner Assumption review draft addressed by local object references."""

    model_config = ConfigDict(extra="forbid")

    assumption_ref: str
    status: AssumptionStatus | None = None
    contradicted_by_discovery_refs: list[str] | None = None
    replacement_assumption_ref: str | None = None

    def operation_payload(
        self,
        *,
        assumption_id: UUID,
        contradicted_by_discovery_ids: list[UUID] | None = None,
        replacement_assumption_id: UUID | None = None,
    ) -> AssumptionStateUpdateOperationPayload:
        """Return the typed operation payload for this Assumption update."""

        payload = self.model_dump(
            mode="python",
            exclude={
                "assumption_ref",
                "contradicted_by_discovery_refs",
                "replacement_assumption_ref",
            },
            exclude_unset=True,
        )
        return AssumptionStateUpdateOperationPayload(
            assumption_id=assumption_id,
            contradicted_by_discovery_ids=contradicted_by_discovery_ids,
            replacement_assumption_id=replacement_assumption_id,
            **payload,
        )


class ConflictFlagDraft(BaseModel):
    """Planner conflict flag addressed by graph-local object references."""

    model_config = ConfigDict(extra="forbid")

    assumption_ref: str
    target_object_type: str = "assumption"
    discovery_ref: str | None = None
    contradicted_by_discovery_ref: str | None = None
    reason: str | None = None

    def operation_payload(
        self,
        *,
        assumption_id: UUID,
        discovery_id: UUID | None = None,
        contradicted_by_discovery_id: UUID | None = None,
    ) -> ConflictFlagOperationPayload:
        """Return the typed operation payload for this conflict flag."""

        payload = self.model_dump(
            mode="python",
            exclude={"assumption_ref", "discovery_ref", "contradicted_by_discovery_ref"},
            exclude_none=True,
        )
        return ConflictFlagOperationPayload(
            assumption_id=assumption_id,
            discovery_id=discovery_id,
            contradicted_by_discovery_id=contradicted_by_discovery_id,
            **payload,
        )


class RequestGroundingContext(BaseModel):
    """Context for resolving relative references in user requests."""

    pass


class PlanningContext(BaseModel):
    """Context for planning Tasks and Hypotheses."""

    pass


class ExecutionPreparationContext(BaseModel):
    """Context for preparing an execution run."""

    pass


class EvidenceValidationContext(BaseModel):
    """Context for validating executor raw observation."""

    pass


class ConclusionContext(BaseModel):
    """Context for synthesizing Discoveries."""

    pass


class AnswerContext(BaseModel):
    """Context for answering user questions."""

    pass


class ConflictReviewContext(BaseModel):
    """Context for conflict detection."""

    pass


class ContextualGrounding(BaseModel):
    """Result of resolving intent against active context."""

    resolved_query: str
    target_task_refs: list[str] = Field(default_factory=list)
    target_profile_refs: list[str] = Field(default_factory=list)


class EvidenceAdmission(BaseModel):
    """Result of structurally validating raw executor output."""

    admitted: bool = False
    evidence_ref: str | None = None
    error_message: str | None = None


class HypothesisEvaluation(BaseModel):
    """Result of evaluating all admitted evidence for a Hypothesis."""

    evaluated: bool = False
    new_status: HypothesisStatus | None = None
    discovery_draft: dict[str, Any] | None = None


class State(BaseModel):
    """Internal Planner state."""

    query: str
    response_text: str | None = None
    request_understanding: RequestUnderstanding | None = None
    contextual_grounding: ContextualGrounding | None = None
    task_selection: TaskSelection | None = None
    execution_preparation: ExecutionPreparation | None = None
    preparation_phase: Literal["draft", "claim"] = "draft"
    execution_revalidation: ExecutionRevalidation | None = None
    prepared_execution: PreparedExecution | None = None
    execution_admission: ExecutionAdmission | None = None
    executor_result: ExecutorResult | None = None
    evidence_admission: EvidenceAdmission | None = None
    hypothesis_evaluation: HypothesisEvaluation | None = None
    execution_review: ExecutionReviewResult | None = None
    session_id: str | None = None
    resume_approval_id: UUID | None = None
    active_session_frame_id: UUID | None = None
    requested_capability: PlannerCapability | None = None
    controlled_placeholder: ControlledPlaceholderResult | None = None
    object_reference_index: dict[str, str] = Field(default_factory=dict)
    history: list[ModelMessage] = Field(default_factory=list)
    task_create_payloads: list[Task] = Field(default_factory=list)
    task_update_payloads: list[TaskUpdateDraft] = Field(default_factory=list)
    task_state_change_payloads: list[TaskStateChangeDraft] = Field(default_factory=list)
    objective_update_payloads: list[ObjectiveUpdateDraft] = Field(default_factory=list)
    assumption_create_payloads: list[Assumption] = Field(default_factory=list)
    assumption_state_update_payloads: list[AssumptionStateUpdateDraft] = Field(default_factory=list)
    conflict_flag_payloads: list[ConflictFlagDraft] = Field(default_factory=list)
    planner_operations: list[PlannerOperation] = Field(default_factory=list)
    operation_ids_to_commit: list[str] | None = None
    operation_batch_id: str | None = None
    commit_purpose: Literal[
        "normal_operations",
        "execution_claim",
        "execution_result",
        "execution_failure",
    ] = "normal_operations"
    requested_interaction_kind: PendingInteractionKind | None = None
    proposal_source: str | None = None
    pending_interaction: PendingUserInteraction | None = None
    resume_payload: dict[str, Any] | None = None
    planner_decision: PlannerDecision | None = None
    user_feedback: str | None = None
    local_workflow_terminated: bool = False
    interaction_error: str | None = None
    hard_stop_code: str | None = None
    hard_stop_message: str | None = None
    controlled_error: ControlledPlannerError | None = None
    commit_result: PlannerCommitResult | None = None

    def bind_object_reference(self, object_type: str, persistent_id: str) -> str:
        """Return a local handle while retaining the durable id in runtime state only."""

        for reference, known_id in self.object_reference_index.items():
            if known_id == persistent_id:
                return reference
        reference = new_local_reference(object_type)
        self.object_reference_index[reference] = persistent_id
        return reference

    def resolve_object_reference(self, reference: str) -> str:
        """Resolve a local handle at a persistence or repository boundary."""

        try:
            return self.object_reference_index[reference]
        except KeyError as exc:
            raise ValueError(f"Unknown local object reference: {reference}") from exc


class Context(BaseModel):
    """Context for the Planner agent."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    database_url: str | None = None
    session_id: str | None = None
    session_frame_id: UUID | None = None
    request_understanding_model: RequestUnderstandingModel | None = None
    governance_mode: GovernanceMode = GovernanceMode.RISK_BASED


class ControlledPlannerError(BaseModel):
    """A user-visible controlled Planner failure without internal object handles."""

    code: str
    message: str


class ControlledPlaceholderResult(BaseModel):
    """Typed, user-visible result for an admitted but deferred capability."""

    error_code: Literal[
        "capability_not_implemented",
        "capability_precondition_failed",
    ]
    capability: PlannerCapability
    node_name: str
    intent: PlannerIntent | None = None
    request_text: str | None = None
    message: str
    future_extension_boundary: str
    unmet_requirements: tuple[str, ...] = ()
    suggested_next_action: str | None = None


class PlannerOutput(BaseModel):
    """Typed, user-visible public result for one Planner invocation."""

    """PydanticAI output schema for planner-authored requests."""

    response_text: str | None = None
    session_frame_id: UUID | None = None
    requested_capability: PlannerCapability | None = None
    pending_interaction: PendingUserInteraction | None = None
    controlled_error: ControlledPlannerError | None = None
    controlled_placeholder: ControlledPlaceholderResult | None = None
    committed_operation_ids: list[UUID] = Field(default_factory=list)
    planner_operations: list[PlannerOperation] = Field(default_factory=list)
    executor_dispatch_ref: str | None = None
    commit_result: PlannerCommitResult | None = None
