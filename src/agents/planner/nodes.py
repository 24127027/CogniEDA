import json
from hashlib import sha256
from typing import Any
from uuid import UUID, uuid4

from langgraph.runtime import Runtime
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlmodel import Session

from application.orchestrator.execution_admission import build_execution_admission_operations
from application.orchestrator.planner_commit import commit_planner_operations
from application.orchestrator.scientific_processing import (
    _execution_operation,
    _method_parameter_hash,
)
from db.models import ExecutionApprovalRecord, PlannerOperationRecord
from db.session import get_session
from memory.retrieval_engine import DiscoveryRetrievalEngine
from memory.session_frame import SessionContextBuilder
from repositories import (
    DataProfileRepository,
    DiscoveryRepository,
    ExecutionApprovalRepository,
    HypothesisRepository,
    PlannerOperationRepository,
    SessionFrameRepository,
    TaskRepository,
)
from repositories.objective_repository import MultipleActiveObjectivesError, ObjectiveRepository
from schemas.artifacts import Hypothesis, Objective, SessionFrame
from schemas.common import TaskContextSummary
from schemas.enums import (
    ContextMode,
    DataProfileLifecycleState,
    ExecutionApprovalStatus,
    HypothesisStatus,
    ObjectiveStatus,
    PlannerNodeName,
    PlannerOperationApprovalState,
    PlannerOperationType,
    TaskKind,
    TaskLifecycleState,
)
from schemas.planner_operations import PlannerOperation
from schemas.provenance import ExecutionApproval
from schemas.retrieval import RetrievalRequest

from ..utilities.nodes_registry import NodeRegistry
from .types import (
    COMMAND_TO_INTENT,
    Context,
    ContextualGrounding,
    ControlledPlannerError,
    ExecutionAdmission,
    ExecutionPreparation,
    ExecutionRevalidation,
    ExecutionSpecification,
    HypothesisDraft,
    ObjectiveCreateDraft,
    ObjectiveUpdateDraft,
    PendingUserInteraction,
    PreparedExecution,
    RequestUnderstanding,
    RequestUnderstandingModel,
    State,
    TaskCreateDraft,
    TaskDecompositionDraft,
    TaskSelection,
    TaskStateChangeDraft,
    TaskUpdateDraft,
    parse_explicit_command,
)

registry = NodeRegistry[State, Context]()
R = registry.R

# --------------------
# Core
# --------------------


class _ConfiguredRequestUnderstandingModel(RequestUnderstandingModel):
    """Adapter over the repository LLM factory for request-only classification."""

    def __init__(self) -> None:
        from agents.llm import ModelConfig, create_agent

        self._agent = create_agent(
            worker="planner",
            config=ModelConfig(),
            deps_type=type(None),
            builtin_tools=[],
        )

    def understand(self, prompt: str) -> RequestUnderstanding:
        result = self._agent.run_sync(prompt, output_type=RequestUnderstanding)
        return RequestUnderstanding.model_validate(result.output)


def _request_understanding_prompt(query: str) -> str:
    """Build the request-only prompt used for deterministic-stage LLM classification."""

    intent_definitions = "\n".join(
        f"- {intent}: classify requests that should be routed to {intent}."
        for intent in COMMAND_TO_INTENT.values()
    )
    return (
        "Classify only the latest raw user request into one allowed planner intent.\n"
        "Return structured output with `intent` and `request_text`.\n"
        "Do not invent IDs, Assumptions, Evidence, Discoveries, factual project state, "
        "or any other research objects. Do not use prior conversation, SessionFrame, "
        "or retrieved research context.\n"
        "Allowed intents:\n"
        f"{intent_definitions}\n\n"
        f"Latest raw user request:\n{query}"
    )


def _invalid_command_understanding(
    original_command: str,
    request_text: str,
) -> RequestUnderstanding:
    supported_commands = tuple(f"/{command}" for command in COMMAND_TO_INTENT)
    return RequestUnderstanding(
        intent=None,
        request_text=request_text,
        source="invalid_command",
        explicit_command=original_command,
        requires_user_correction=True,
        error_message=(
            f"Unsupported command '{original_command}'. Supported commands: "
            f"{', '.join(supported_commands)}."
        ),
        supported_commands=supported_commands,
    )


def _invalid_llm_understanding(query: str) -> RequestUnderstanding:
    return RequestUnderstanding(
        intent=None,
        request_text=query,
        source="invalid_llm",
        requires_user_correction=True,
        error_message=(
            "Unable to classify the request. Please restate it or use a supported command."
        ),
        supported_commands=tuple(f"/{command}" for command in COMMAND_TO_INTENT),
    )


@registry.register()
def understand_request(state: State, runtime: Runtime[Context]) -> State:
    """
    LLM interprets the user's latest message.

    The model identifies the user's intent and extracts any information
    needed for subsequent planning. This step intentionally does not
    consume Session Frame context so intent recognition is based solely
    on the user's request.
    """
    command = parse_explicit_command(state.query)
    if command is not None:
        intent = COMMAND_TO_INTENT.get(command.command)
        if intent is None:
            state.request_understanding = _invalid_command_understanding(
                command.original_command,
                command.request_text,
            )
        else:
            state.request_understanding = RequestUnderstanding(
                intent=intent,
                request_text=command.request_text,
                source="explicit_command",
                explicit_command=command.command,
            )
        return state

    context = _runtime_context(runtime)
    model = (
        context.request_understanding_model
        if context is not None and context.request_understanding_model is not None
        else _ConfiguredRequestUnderstandingModel()
    )
    try:
        state.request_understanding = RequestUnderstanding.model_validate(
            model.understand(_request_understanding_prompt(state.query))
        )
    except Exception:
        state.request_understanding = _invalid_llm_understanding(state.query)
    return state


def route_intent(state: State, runtime: Runtime[Context]) -> str:
    """Route the user's intent to the appropriate node and return a routing key."""
    understanding = state.request_understanding
    if (
        understanding is None
        or understanding.requires_user_correction
        or understanding.intent is None
    ):
        return "invalid_request"
    if understanding.intent == "answer":
        return "check_answerability"
    return understanding.intent


def route_entry(state: State, runtime: Runtime[Context]) -> str:
    """Resume only through a durable approval identifier when one is supplied."""

    if state.resume_operation_ids or state.resume_operation_proposal_id is not None:
        return "resume_planner_operations"
    return "resume_execution" if state.resume_approval_id is not None else "understand_request"


@registry.register()
def contextual_grounding(state: State, runtime: Runtime[Context]) -> State:
    """Resolve relative references using SessionFrame context."""

    understanding = state.request_understanding
    if understanding is None or understanding.intent != "decompose":
        return state
    try:
        task_id = UUID(understanding.request_text)
    except ValueError:
        state.controlled_error = ControlledPlannerError(
            code="malformed_decomposition_parent",
            message="/decompose requires one exact parent Task UUID.",
        )
        return state
    session = _read_session(runtime)
    if session is None:
        state.controlled_error = ControlledPlannerError(
            code="decomposition_store_unavailable",
            message="Task decomposition requires a configured planner database.",
        )
        return state
    try:
        parent = TaskRepository(session).get_by_id(task_id)
    finally:
        session.close()
    if parent is None:
        state.controlled_error = ControlledPlannerError(
            code="unknown_decomposition_parent",
            message="The requested parent Task does not exist.",
        )
        return state
    state.contextual_grounding = ContextualGrounding(
        resolved_query=understanding.request_text,
        target_task_refs=[state.bind_object_reference("task", str(parent.task_id))],
    )
    return state


@registry.register()
def check_answerability(state: State, runtime: Runtime[Context]) -> State:
    """Gate: determine if we have adequate valid basis to answer a question."""

    # TODO: Assess evidence-backed answerability without using assumptions as premises.
    pass


@registry.register()
def invalid_request(state: State, runtime: Runtime[Context]) -> State:
    """Terminal controlled route for unsupported or unclassifiable requests."""

    return state


# --------------------
# Question answering
# --------------------


@registry.register()
def answer_question(state: State, runtime: Runtime[Context]) -> None:
    """Answer the user's question using the relevant research context."""

    # TODO: Implement question answering using SessionFrame context.
    pass


# --------------------
# Research planning
# --------------------


@registry.register()
def propose_questions(state: State, runtime: Runtime[Context]) -> None:
    """Propose research directions using the relevant planning context."""

    # TODO: Implement research-direction proposal from planning context.
    pass


class _ConfiguredTaskDecompositionModel:
    """Adapter for the bounded decomposition structured-output request."""

    def __init__(self) -> None:
        from agents.llm import ModelConfig, create_agent

        self._agent = create_agent(
            worker="planner", config=ModelConfig(), deps_type=type(None), builtin_tools=[]
        )

    def draft(self, prompt: str) -> TaskDecompositionDraft:
        result = self._agent.run_sync(prompt, output_type=TaskDecompositionDraft)
        return TaskDecompositionDraft.model_validate(result.output)


@registry.register()
def expand_plan(state: State, runtime: Runtime[Context]) -> State:
    """Draft bounded, child-specific Task operations for one approved parent."""

    context = _runtime_context(runtime)
    grounding = state.contextual_grounding
    if (
        state.request_understanding is None
        or state.request_understanding.intent != "decompose"
        or grounding is None
        or len(grounding.target_task_refs) != 1
    ):
        state.controlled_error = ControlledPlannerError(
            code="invalid_decomposition_request",
            message="Decomposition requires one resolved parent Task.",
        )
        return state
    if context is None or context.database_url is None or context.session_frame_id is None:
        state.controlled_error = ControlledPlannerError(
            code="decomposition_context_unavailable",
            message="Decomposition requires a configured database and active SessionFrame.",
        )
        return state

    parent_ref = grounding.target_task_refs[0]
    try:
        parent_task_id = UUID(state.resolve_object_reference(parent_ref))
    except ValueError:
        state.controlled_error = ControlledPlannerError(
            code="invalid_decomposition_parent",
            message="The resolved parent Task is no longer available.",
        )
        return state

    session = get_session(context.database_url)
    try:
        parent = TaskRepository(session).get_by_id(parent_task_id)
        frame = SessionFrameRepository(session).get_by_id(context.session_frame_id)
        if parent is None or frame is None:
            state.controlled_error = ControlledPlannerError(
                code="decomposition_context_missing",
                message="The parent Task or active SessionFrame is no longer available.",
            )
            return state
        objective = ObjectiveRepository(session).get_active()
        if objective is None:
            state.controlled_error = ControlledPlannerError(
                code="decomposition_objective_missing",
                message="Decomposition retrieval requires an active Objective.",
            )
            return state

        planning = SessionContextBuilder().build(frame, mode=ContextMode.PLANNING)
        active_profile_id = (
            planning.data_profile_refs[0] if planning.data_profile_refs else parent.profile_id
        )
        if active_profile_id is None:
            state.controlled_error = ControlledPlannerError(
                code="decomposition_data_profile_missing",
                message="Decomposition retrieval requires an active DataProfile.",
            )
            return state
        active_profile = DataProfileRepository(session).get_by_id(active_profile_id)
        if (
            active_profile is None
            or active_profile.lifecycle_state != DataProfileLifecycleState.ACTIVE
        ):
            state.controlled_error = ControlledPlannerError(
                code="decomposition_data_profile_unavailable",
                message="Decomposition retrieval requires a current active DataProfile.",
            )
            return state
        retrieval_request = RetrievalRequest(
            objective_id=objective.objective_id,
            active_data_profile_id=active_profile_id,
            session_frame_id=frame.session_frame_id,
            parent_task_id=parent.task_id,
            query_text=state.request_understanding.request_text,
        )

        engine = DiscoveryRetrievalEngine(session)
        retrieval_result = engine.retrieve(retrieval_request, frame)

        selectable_candidates: dict[str, UUID] = {}
        candidate_explanations: dict[str, dict[str, object]] = {}
        parent_motivation_refs: list[str] = []
        other_candidate_refs: list[str] = []

        for item in retrieval_result.motivation_candidates:
            reference = state.bind_object_reference("discovery", str(item.discovery_id))
            selectable_candidates[reference] = item.discovery_id
            parent_motivation_refs.append(reference)
            candidate_explanations[reference] = _retrieval_candidate_explanation(item)

        for item in retrieval_result.other_relevant_discoveries:
            reference = state.bind_object_reference("discovery", str(item.discovery_id))
            other_candidate_refs.append(reference)
            candidate_explanations[reference] = _retrieval_candidate_explanation(item)

        active_profile_ref = state.bind_object_reference(
            "data_profile", str(active_profile.profile_id)
        )

        prompt = _task_decomposition_prompt(
            parent_ref=parent_ref,
            parent=parent,
            planning=planning,
            parent_motivation_refs=parent_motivation_refs,
            other_candidate_refs=other_candidate_refs,
            candidate_explanations=candidate_explanations,
            retrieval_exclusion_notes=retrieval_result.exclusion_notes,
            active_profile_ref=active_profile_ref,
        )
    finally:
        session.close()

    model = context.task_decomposition_model or _ConfiguredTaskDecompositionModel()
    try:
        draft = TaskDecompositionDraft.model_validate(model.draft(prompt))
        if draft.parent_task_ref != parent_ref:
            raise ValueError("The proposal parent is not the resolved parent Task.")
        operations, frame_operation = _decomposition_operations(
            state=state,
            parent=parent,
            frame=frame,
            draft=draft,
            candidate_refs=selectable_candidates,
            active_profile_ref=active_profile_ref,
            active_profile_id=active_profile.profile_id,
        )
    except Exception:
        state.controlled_error = ControlledPlannerError(
            code="invalid_decomposition_proposal",
            message="Unable to produce a valid bounded child-Task proposal.",
        )
        return state

    state.task_decomposition_payloads.append(draft)
    state.planner_operations.extend([*operations, frame_operation])
    state.requested_interaction_kind = "planner_operation_approval"
    return state


def _task_decomposition_prompt(
    *,
    parent_ref: str,
    parent: Any,
    planning: Any,
    parent_motivation_refs: list[str],
    other_candidate_refs: list[str],
    candidate_explanations: dict[str, dict[str, object]],
    retrieval_exclusion_notes: list[str],
    active_profile_ref: str,
) -> str:
    """Build a bounded planning-only prompt; no global Discovery retrieval occurs."""

    return (
        "Decompose one parent Task into child Task proposals. Return only the typed "
        "TaskDecompositionDraft. Every child must explicitly provide "
        "motivated_by_discovery_refs; [] is valid and means no motivation. Do not use "
        "UUIDs: use only the selectable local references supplied below. A child may "
        "select any subset of the selectable candidates; never inherit parent "
        "motivation implicitly. "
        "Rationale and readiness are proposal provenance, not Evidence or Discovery. "
        "Readiness does not authorize execution.\n\n"
        f"Parent local reference: {parent_ref}\n"
        f"Parent title: {parent.title}\nParent description: {parent.description}\n"
        f"Objective constraints: {planning.objective_snapshot}\n"
        "Planning Assumptions: "
        f"{json.dumps([item.model_dump(mode='json') for item in planning.assumptions])}\n"
        f"Parent direct-motivation candidates: {parent_motivation_refs}\n"
        f"Other bounded Discovery candidates: {other_candidate_refs}\n"
        f"Candidate explanations: {json.dumps(candidate_explanations)}\n"
        f"Retrieval warnings: {json.dumps(retrieval_exclusion_notes)}\n"
        "Other bounded Discovery candidates are context-only and must not appear in "
        "motivated_by_discovery_refs. No other Task or Discovery reference is valid.\n"
        "If a child is 'ready_analytical', it should include the full execution contract: "
        f"data_profile_ref (use {active_profile_ref}), variables, evidence_expectation, "
        "hypothesis_statement, claim_type, decision_rule, validation_method, executor_id, "
        "method_parameters, and deterministic_seed. These are planning fields; do not author "
        "a durable DataProfile UUID or an analytical_specification dictionary."
    )


def _retrieval_candidate_explanation(item: Any) -> dict[str, object]:
    """Expose retrieval reasons to the planning model without durable identifiers."""

    return {
        "claim": item.claim_statement,
        "lifecycle_state": item.lifecycle_state.value,
        "relevance_score": item.relevance_score,
        "structural_relations": item.structural_relations_used,
        "inclusion_reasons": item.inclusion_reasons,
        "warnings": item.flags,
        "is_pinned": item.is_pinned,
        "eligible_for_motivation": item.eligible_for_motivation,
    }


def _decomposition_operations(
    *,
    state: State,
    parent: Any,
    frame: Any,
    draft: TaskDecompositionDraft,
    candidate_refs: dict[str, UUID],
    active_profile_ref: str,
    active_profile_id: UUID,
) -> tuple[list[PlannerOperation], PlannerOperation]:
    """Translate one validated draft to atomic child and frame operations."""

    operations: list[PlannerOperation] = []
    child_ids: list[UUID] = []
    child_summaries: list[TaskContextSummary] = []
    for child in draft.child_task_proposals:
        if child.parent_task_ref != draft.parent_task_ref:
            raise ValueError("Child proposal names another parent.")
        if any(reference not in candidate_refs for reference in child.motivated_by_discovery_refs):
            raise ValueError(
                "Child proposal references a Discovery outside the bounded candidates."
            )
        if child.readiness_status == "ready_analytical":
            if child.data_profile_ref != active_profile_ref:
                raise ValueError(
                    "Analytical child must use the bounded active DataProfile reference."
                )
        elif child.data_profile_ref is not None:
            raise ValueError("Non-analytical child cannot bind an execution DataProfile.")
        child_id = uuid4()
        child_ids.append(child_id)
        profile_id = (
            UUID(state.resolve_object_reference(child.data_profile_ref))
            if child.data_profile_ref is not None
            else None
        )
        payload = child.operation_payload(
            task_id=child_id,
            parent_task_id=parent.task_id,
            motivated_by_discovery_ids=[
                candidate_refs[ref] for ref in child.motivated_by_discovery_refs
            ],
            parent_task_updated_at=parent.updated_at,
            profile_id=profile_id,
            motivation_data_profile_id=active_profile_id,
        )
        operations.append(
            PlannerOperation(
                session_id=state.session_id or "default",
                operation_type=PlannerOperationType.CREATE_TASK,
                payload=payload.model_dump(mode="json"),
                produced_by_node=PlannerNodeName.EXPAND_PLAN,
            )
        )
        child_summaries.append(
            TaskContextSummary(
                task_id=child_id,
                title=child.title,
                lifecycle_state=TaskLifecycleState.ACTIVE.value,
                parent_task_id=parent.task_id,
            )
        )
    updated_frame = frame.model_copy(
        update={
            "session_frame_id": uuid4(),
            "parent_session_frame_id": frame.session_frame_id,
            "active_task_refs": [*frame.active_task_refs, *child_ids],
            "active_tasks": [*frame.active_tasks, *child_summaries],
            "inclusion_reasons": {
                **frame.inclusion_reasons,
                **{
                    str(task_id): "approved decomposition child of the selected parent Task"
                    for task_id in child_ids
                },
            },
        }
    )
    return operations, PlannerOperation(
        session_id=state.session_id or "default",
        operation_type=PlannerOperationType.UPDATE_SESSION_FRAME,
        payload=updated_frame.model_dump(mode="json"),
        produced_by_node=PlannerNodeName.EXPAND_PLAN,
    )


# --------------------
# Task management
# --------------------


class TaskManagementDraft(BaseModel):
    """Structured output for translating a user request into task operations."""

    model_config = ConfigDict(extra="forbid")

    task_create_payloads: list[TaskCreateDraft] = Field(default_factory=list)
    task_update_payloads: list[TaskUpdateDraft] = Field(default_factory=list)
    task_state_change_payloads: list[TaskStateChangeDraft] = Field(default_factory=list)

    @model_validator(mode="after")
    def _reject_model_authored_discovery_motivation(self) -> "TaskManagementDraft":
        """Discovery motivation is planner provenance, not general proposal output."""

        if any(
            "motivated_by_discovery_ids" in update.model_fields_set
            for update in self.task_update_payloads
        ):
            raise ValueError(
                "Task-management proposals cannot author Discovery motivation references."
            )
        return self


class _ConfiguredTaskManagementModel:
    """Adapter over the repository LLM factory for task drafting."""

    def __init__(self) -> None:
        from agents.llm import ModelConfig, create_agent

        self._agent = create_agent(
            worker="planner",
            config=ModelConfig(),
            deps_type=type(None),
            builtin_tools=[],
        )

    def draft(self, prompt: str) -> TaskManagementDraft:
        result = self._agent.run_sync(prompt, output_type=TaskManagementDraft)
        return TaskManagementDraft.model_validate(result.output)


def _task_management_prompt(
    query: str,
    state: State,
    *,
    motivation_candidate_refs: list[str],
    other_relevant_discovery_refs: list[str],
    candidate_explanations: dict[str, dict[str, object]],
    retrieval_exclusion_notes: list[str],
) -> str:
    """Build the prompt for drafting task operations."""

    references = ", ".join(sorted(state.object_reference_index)) or "(none)"
    return (
        "Translate the user's task management request into task operations.\n"
        "Do not invent UUIDs or use identifiers not listed below. The Planner allocates new "
        "Task ids, which become durable only after commit. Use listed local references for "
        "updates, parent tasks, profiles, and supersession. A root Task may explicitly select "
        "Discovery motivation "
        "only from the bounded motivation candidates below. Put only those local references "
        "in selected_motivating_discovery_refs. Context-only references cannot be selected. "
        "Do not expose or author durable Discovery UUIDs. Child motivation belongs to "
        "/decompose, not this surface.\n"
        f"Allowed existing local references: {references}\n"
        f"Motivation candidate local references: {motivation_candidate_refs}\n"
        f"Other relevant context-only Discovery references: {other_relevant_discovery_refs}\n"
        f"Candidate explanations: {json.dumps(candidate_explanations)}\n"
        f"Retrieval warnings: {json.dumps(retrieval_exclusion_notes)}\n"
        f"Latest raw user request:\n{query}"
    )


def _root_task_motivation_context(
    state: State,
    context: Context | None,
) -> tuple[
    dict[str, UUID],
    list[str],
    dict[str, dict[str, object]],
    list[str],
    SessionFrame | None,
    UUID | None,
]:
    """Return one bounded planning-only candidate set for root Task motivation."""

    if context is None or context.database_url is None or context.session_frame_id is None:
        return {}, [], {}, [], None, None
    session = get_session(context.database_url)
    try:
        frame = SessionFrameRepository(session).get_by_id(context.session_frame_id)
        objective = ObjectiveRepository(session).get_active()
        if frame is None or objective is None:
            return {}, [], {}, [], frame, None
        planning = SessionContextBuilder().build(frame, mode=ContextMode.PLANNING)
        active_profile_id = planning.data_profile_refs[0] if planning.data_profile_refs else None
        if active_profile_id is None:
            return {}, [], {}, [], frame, None
        active_profile = DataProfileRepository(session).get_by_id(active_profile_id)
        if (
            active_profile is None
            or active_profile.lifecycle_state != DataProfileLifecycleState.ACTIVE
            or not active_profile.accepted_as_ground_truth
        ):
            return {}, [], {}, [], frame, None
        retrieval_result = DiscoveryRetrievalEngine(session).retrieve(
            RetrievalRequest(
                objective_id=objective.objective_id,
                active_data_profile_id=active_profile_id,
                session_frame_id=frame.session_frame_id,
                query_text=(
                    state.request_understanding.request_text
                    if state.request_understanding is not None
                    else state.query
                ),
            ),
            frame,
        )
        selectable: dict[str, UUID] = {}
        contextual: list[str] = []
        explanations: dict[str, dict[str, object]] = {}
        for item in retrieval_result.motivation_candidates:
            reference = state.bind_object_reference("discovery", str(item.discovery_id))
            selectable[reference] = item.discovery_id
            explanations[reference] = _retrieval_candidate_explanation(item)
        for item in retrieval_result.other_relevant_discoveries:
            reference = state.bind_object_reference("discovery", str(item.discovery_id))
            contextual.append(reference)
            explanations[reference] = _retrieval_candidate_explanation(item)
        return (
            selectable,
            contextual,
            explanations,
            retrieval_result.exclusion_notes,
            frame,
            active_profile_id,
        )
    finally:
        session.close()


@registry.register()
def manage_tasks(state: State, runtime: Runtime[Context]) -> State:
    """
    Draft Task operations without directly mutating persistent Task records.

    Later workflow code can decide which operations require user approval before
    commit applies them.
    """
    context = _runtime_context(runtime)
    (
        motivation_candidates,
        contextual_discovery_refs,
        motivation_explanations,
        motivation_warnings,
        source_frame,
        motivation_profile_id,
    ) = _root_task_motivation_context(state, context)
    has_existing_drafts = any(
        (
            state.task_create_payloads,
            state.task_update_payloads,
            state.task_state_change_payloads,
        )
    )
    if not has_existing_drafts:
        model = context.task_management_model if context else None
        if model is None:
            model = _ConfiguredTaskManagementModel()
        try:
            draft_result = model.draft(
                _task_management_prompt(
                    state.query,
                    state,
                    motivation_candidate_refs=list(motivation_candidates),
                    other_relevant_discovery_refs=contextual_discovery_refs,
                    candidate_explanations=motivation_explanations,
                    retrieval_exclusion_notes=motivation_warnings,
                )
            )
            state.task_create_payloads.extend(draft_result.task_create_payloads)
            state.task_update_payloads.extend(draft_result.task_update_payloads)
            state.task_state_change_payloads.extend(draft_result.task_state_change_payloads)
        except Exception:
            state.controlled_error = ControlledPlannerError(
                code="task_proposal_unavailable",
                message="Unable to produce a valid task proposal from the request.",
            )
            return state

    session_id = _session_id(state, runtime)
    operations: list[PlannerOperation] = []
    root_task_summaries: list[TaskContextSummary] = []
    try:
        for task in state.task_create_payloads:
            is_governed_root_motivation = (
                source_frame is not None
                and task.parent_task_ref is None
                and "selected_motivating_discovery_refs" in task.model_fields_set
            )
            task_id = uuid4() if is_governed_root_motivation else None
            parent_task_id = (
                UUID(state.resolve_object_reference(task.parent_task_ref))
                if task.parent_task_ref is not None
                else None
            )
            profile_id = (
                UUID(state.resolve_object_reference(task.data_profile_ref))
                if task.data_profile_ref is not None
                else None
            )
            if task.selected_motivating_discovery_refs and task.parent_task_ref is not None:
                raise ValueError("Only root Tasks can use the governed root-motivation surface.")
            if any(
                reference not in motivation_candidates
                for reference in task.selected_motivating_discovery_refs
            ):
                raise ValueError("Task selected a Discovery outside the bounded candidates.")
            motivated_ids = [
                motivation_candidates[reference]
                for reference in task.selected_motivating_discovery_refs
            ]
            operations.append(
                PlannerOperation(
                    session_id=session_id,
                    operation_type=PlannerOperationType.CREATE_TASK,
                    payload=task.operation_payload(
                        task_id=task_id,
                        parent_task_id=parent_task_id,
                        profile_id=profile_id,
                        motivated_by_discovery_ids=motivated_ids,
                        motivation_data_profile_id=motivation_profile_id,
                    ).model_dump(mode="json", exclude_none=True),
                    produced_by_node=PlannerNodeName.MANAGE_TASKS,
                )
            )
            if task_id is not None:
                root_task_summaries.append(
                    TaskContextSummary(
                        task_id=task_id,
                        title=task.title,
                        lifecycle_state=TaskLifecycleState.ACTIVE.value,
                    )
                )
        for task_update in state.task_update_payloads:
            parent_task_id = (
                UUID(state.resolve_object_reference(task_update.parent_task_ref))
                if task_update.parent_task_ref is not None
                else None
            )
            profile_id = (
                UUID(state.resolve_object_reference(task_update.data_profile_ref))
                if task_update.data_profile_ref is not None
                else None
            )
            superseded_by_task_id = (
                UUID(state.resolve_object_reference(task_update.superseded_by_task_ref))
                if task_update.superseded_by_task_ref is not None
                else None
            )
            operations.append(
                PlannerOperation(
                    session_id=session_id,
                    operation_type=PlannerOperationType.UPDATE_TASK,
                    payload=task_update.operation_payload(
                        task_id=UUID(state.resolve_object_reference(task_update.task_ref)),
                        parent_task_id=parent_task_id,
                        profile_id=profile_id,
                        superseded_by_task_id=superseded_by_task_id,
                    ).model_dump(mode="json", exclude_unset=True),
                    produced_by_node=PlannerNodeName.MANAGE_TASKS,
                )
            )
        for task_state_change in state.task_state_change_payloads:
            operations.append(
                PlannerOperation(
                    session_id=session_id,
                    operation_type=PlannerOperationType.CHANGE_TASK_STATE,
                    payload=task_state_change.operation_payload(
                        task_id=UUID(state.resolve_object_reference(task_state_change.task_ref)),
                    ).model_dump(mode="json", exclude_unset=True),
                    produced_by_node=PlannerNodeName.MANAGE_TASKS,
                )
            )
    except ValueError:
        state.controlled_error = ControlledPlannerError(
            code="invalid_task_proposal_reference",
            message="The task proposal contains an unknown or invalid object reference.",
        )
        return state
    if root_task_summaries and source_frame is not None:
        updated_frame = source_frame.model_copy(
            update={
                "session_frame_id": uuid4(),
                "parent_session_frame_id": source_frame.session_frame_id,
                "active_task_refs": [
                    *source_frame.active_task_refs,
                    *(summary.task_id for summary in root_task_summaries),
                ],
                "active_tasks": [*source_frame.active_tasks, *root_task_summaries],
                "inclusion_reasons": {
                    **source_frame.inclusion_reasons,
                    **{
                        str(summary.task_id): "approved governed root Task"
                        for summary in root_task_summaries
                    },
                },
            }
        )
        operations.append(
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.UPDATE_SESSION_FRAME,
                payload=updated_frame.model_dump(mode="json"),
                produced_by_node=PlannerNodeName.MANAGE_TASKS,
            )
        )
    state.planner_operations.extend(operations)
    return state


@registry.register()
def select_task(state: State, runtime: Runtime[Context]) -> State:
    """Resolve an external Task id once, then use only a local reference in the graph."""

    request_text = (
        state.request_understanding.request_text if state.request_understanding is not None else ""
    )
    if not request_text:
        state.task_selection = TaskSelection(
            error_code="missing_task_reference",
            error_message="/execute requires one exact Task ID.",
        )
        return state

    try:
        task_id = UUID(request_text)
    except ValueError:
        state.task_selection = TaskSelection(
            error_code="malformed_task_reference",
            error_message="/execute requires one exact UUID Task ID.",
        )
        return state

    session = _read_session(runtime)
    if session is None:
        state.task_selection = TaskSelection(
            error_code="execution_store_unavailable",
            error_message="Execution requires a configured planner database.",
        )
        return state
    try:
        task = TaskRepository(session).get_by_id(task_id)
    finally:
        session.close()
    if task is None:
        state.task_selection = TaskSelection(
            error_code="unknown_task_id",
            error_message="The requested Task does not exist.",
        )
        return state

    task_ref = state.bind_object_reference("task", str(task.task_id))
    state.task_selection = TaskSelection(task_ref=task_ref, selected=True)
    return state


# --------------------
# Execution
# --------------------


@registry.register()
def prepare_execution(state: State, runtime: Runtime[Context]) -> State:
    """Compile an admitted Task specification into one transient Hypothesis draft."""

    selection = state.task_selection
    if selection is None or not selection.selected or selection.task_ref is None:
        return _execution_not_prepared(state, "task_not_selected", "No Task was selected.")
    try:
        task_id = UUID(state.resolve_object_reference(selection.task_ref))
    except ValueError:
        return _execution_not_prepared(
            state,
            "unknown_task_reference",
            "The selected local Task reference cannot be resolved.",
        )
    session = _read_session(runtime)
    if session is None:
        return _execution_not_prepared(
            state,
            "execution_store_unavailable",
            "Execution requires a configured planner database.",
        )
    try:
        task_repository = TaskRepository(session)
        task = task_repository.get_by_id(task_id)
        has_children = bool(task_repository.list(parent_task_id=task_id)) if task else False
    finally:
        session.close()
    if task is None:
        return _execution_not_prepared(
            state,
            "unknown_task_reference",
            "The selected Task no longer exists.",
        )
    if task.lifecycle_state != TaskLifecycleState.ACTIVE:
        return _execution_not_prepared(state, "task_not_active", "Task must be active.")
    if task.task_kind != TaskKind.ANALYTICAL:
        return _execution_not_prepared(state, "task_not_analytical", "Task must be analytical.")
    if task.profile_id is None:
        return _execution_not_prepared(
            state, "missing_data_profile", "Task must reference one DataProfile."
        )
    if task.analytical_specification is None:
        return _execution_not_prepared(
            state,
            "missing_analytical_specification",
            "Task requires a structured analytical specification.",
        )
    specification = task.analytical_specification
    if specification.data_profile_id != task.profile_id:
        return _execution_not_prepared(
            state,
            "profile_specification_mismatch",
            "Task and analytical specification must reference the same DataProfile.",
        )

    session = _read_session(runtime)
    if session is None:
        return _execution_not_prepared(
            state,
            "execution_store_unavailable",
            "Execution requires a configured planner database.",
        )
    try:
        profile = DataProfileRepository(session).get_by_id(task.profile_id)
        existing_hypotheses = HypothesisRepository(session).list(task_id=task.task_id)
        existing_discovery_hypothesis_ids = {
            discovery.hypothesis_id for discovery in DiscoveryRepository(session).list()
        }
    finally:
        session.close()
    if has_children:
        return _execution_not_prepared(
            state, "task_has_child_tasks", "Parent Tasks cannot execute analytically."
        )
    if profile is None:
        return _execution_not_prepared(
            state, "unknown_data_profile", "The Task DataProfile does not exist."
        )
    if not (
        profile.lifecycle_state == DataProfileLifecycleState.ACTIVE
        and profile.accepted_as_ground_truth
    ):
        return _execution_not_prepared(
            state, "data_profile_not_accepted", "The Task DataProfile is not accepted and active."
        )
    if not task.variables:
        return _execution_not_prepared(
            state,
            "missing_task_variables",
            "An analytical Task must identify grounded variables or metrics.",
        )
    if not task.evidence_expectation:
        return _execution_not_prepared(
            state,
            "missing_task_evidence_expectation",
            "An analytical Task must define its evidence expectation.",
        )
    unknown_bindings = sorted(
        set(specification.variable_bindings) - set(profile.schema_summary.column_order)
    )
    if unknown_bindings:
        return _execution_not_prepared(
            state,
            "ungrounded_variable_binding",
            "Analytical variable bindings must exist in the accepted DataProfile schema: "
            f"{', '.join(unknown_bindings)}.",
        )
    if not task.can_generate_hypothesis(
        has_child_tasks=has_children,
        data_profile_accepted=True,
    ):
        return _execution_not_prepared(
            state,
            "task_not_execution_ready",
            "The Task does not satisfy the terminal analytical execution contract.",
        )
    existing_hypothesis = existing_hypotheses[0] if len(existing_hypotheses) == 1 else None
    if len(existing_hypotheses) > 1:
        return _execution_not_prepared(
            state,
            "multiple_hypotheses_for_task",
            "A Task has more than one Hypothesis and requires recovery review.",
        )
    if existing_hypothesis is not None:
        if existing_hypothesis.hypothesis_id in existing_discovery_hypothesis_ids:
            return _execution_not_prepared(
                state,
                "hypothesis_already_finalized",
                "The Task Hypothesis already has a final Discovery.",
            )
        if existing_hypothesis.status in {
            HypothesisStatus.CONFIRMED,
            HypothesisStatus.CONTRADICTED,
            HypothesisStatus.INCONCLUSIVE,
            HypothesisStatus.INSUFFICIENT_EVIDENCE,
            HypothesisStatus.CANCELLED,
            HypothesisStatus.ARCHIVED,
        }:
            return _execution_not_prepared(
                state,
                "hypothesis_not_retryable",
                "The Task Hypothesis is terminal and cannot be dispatched again.",
            )

    profile_ref = state.bind_object_reference("data_profile", str(profile.profile_id))
    hypothesis = HypothesisDraft(
        statement=specification.hypothesis_statement,
        variables=specification.variable_bindings,
        scope=specification.scope,
        validation_method=specification.validation_method,
        evidence_expectation=specification.evidence_expectation,
    )
    state.prepared_execution = PreparedExecution(
        task_ref=selection.task_ref,
        data_profile_ref=profile_ref,
        task_title=task.title,
        dataset_path=profile.dataset_path,
        hypothesis=hypothesis,
        specification=ExecutionSpecification(
            claim_type=specification.claim_type,
            variable_bindings=specification.variable_bindings,
            scope=specification.scope,
            evidence_expectation=specification.evidence_expectation,
            decision_rule=specification.decision_rule,
            validation_method=specification.validation_method,
            executor_id=specification.executor_id,
            method_parameters=specification.method_parameters,
        ),
        deterministic_seed=specification.deterministic_seed,
        hypothesis_ref=(
            state.bind_object_reference("hypothesis", str(existing_hypothesis.hypothesis_id))
            if existing_hypothesis is not None
            else None
        ),
        contract_fingerprint=_execution_contract_fingerprint(task, profile, specification),
    )
    state.execution_preparation = ExecutionPreparation(prepared=True)
    return state


@registry.register()
def commit_execution_contract(state: State, runtime: Runtime[Context]) -> State:
    """Atomically persist Hypothesis and ExecutionRun before dispatch."""
    session_id = _session_id(state, runtime)
    prepared = state.prepared_execution
    if prepared is None or state.execution_revalidation is None:
        return state
    if not state.execution_revalidation.valid:
        state.hard_stop_code = state.execution_revalidation.error_code or "execution_not_authorized"
        state.hard_stop_message = (
            state.execution_revalidation.error_message
            or "The execution contract has not been approved."
        )
        return state

    try:
        task_id = UUID(state.resolve_object_reference(prepared.task_ref))
        profile_id = UUID(state.resolve_object_reference(prepared.data_profile_ref))
    except ValueError as exc:
        state.hard_stop_code = "unknown_execution_reference"
        state.hard_stop_message = str(exc)
        return state

    context = _runtime_context(runtime)
    if context is None or context.database_url is None:
        state.hard_stop_code = "execution_store_unavailable"
        state.hard_stop_message = "Execution requires a configured planner database."
        return state

    session = get_session(context.database_url)
    try:
        approval_id_text = (
            state.pending_interaction.payload.get("execution_approval_id")
            if state.pending_interaction is not None
            else None
        )
        approval_id = UUID(str(approval_id_text))
        approval_record = session.get(ExecutionApprovalRecord, approval_id)
        if (
            approval_record is None
            or approval_record.session_id != (session_id or "default")
            or approval_record.status != ExecutionApprovalStatus.APPROVED
            or approval_record.contract_fingerprint != prepared.contract_fingerprint
            or approval_record.task_id != task_id
            or approval_record.profile_id != profile_id
        ):
            raise ValueError("The execution approval is stale or has already been consumed.")
        task = TaskRepository(session).get_by_id(task_id)
        profile = DataProfileRepository(session).get_by_id(profile_id)
        if task is None or profile is None:
            raise ValueError("Task or DataProfile missing during revalidation.")
        if (
            task.lifecycle_state != TaskLifecycleState.ACTIVE
            or task.task_kind != TaskKind.ANALYTICAL
            or task.profile_id != profile_id
            or task.analytical_specification is None
            or not profile.accepted_as_ground_truth
            or profile.lifecycle_state != DataProfileLifecycleState.ACTIVE
        ):
            raise ValueError("The persisted Task or DataProfile is no longer execution-ready.")
        current_fingerprint = _execution_contract_fingerprint(task, profile, prepared.specification)
        if current_fingerprint != prepared.contract_fingerprint:
            raise ValueError("The execution contract is stale (underlying data changed).")

        hypothesis: Hypothesis
        if prepared.hypothesis_ref is None:
            hypothesis = Hypothesis(
                task_id=task_id,
                profile_id=profile_id,
                statement=prepared.hypothesis.statement,
                variables=prepared.hypothesis.variables,
                scope=prepared.hypothesis.scope,
                validation_method=prepared.hypothesis.validation_method,
                evidence_expectation=prepared.hypothesis.evidence_expectation,
                status=HypothesisStatus.TESTING,
            )
            hypothesis_operation = _execution_operation(
                session_id,
                PlannerOperationType.CREATE_HYPOTHESIS,
                hypothesis,
                PlannerNodeName.PREPARE_EXECUTION,
            )
        else:
            hypothesis_id = UUID(state.resolve_object_reference(prepared.hypothesis_ref))
            hypothesis = HypothesisRepository(session).get_by_id(hypothesis_id)
            if hypothesis is None:
                raise ValueError("Approved execution references a missing Hypothesis.")
            hypothesis_operation = PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.CHANGE_HYPOTHESIS_STATE,
                payload={
                    "hypothesis_id": str(hypothesis.hypothesis_id),
                    "status": HypothesisStatus.TESTING.value,
                },
                produced_by_node=PlannerNodeName.PREPARE_EXECUTION,
                approval_state=PlannerOperationApprovalState.NOT_REQUIRED,
            )

        execution_run, admission_operations = build_execution_admission_operations(
            session_id=session_id,
            task_id=task_id,
            hypothesis_id=hypothesis.hypothesis_id,
            executor_type=prepared.specification.executor_id,
            method_id=prepared.specification.validation_method,
            parameter_hash=_method_parameter_hash(prepared.specification.method_parameters),
            prepared_payload=prepared.model_dump(mode="json"),
        )

        approval_record.status = ExecutionApprovalStatus.CONSUMED
        session.add(approval_record)
        operations = [
            operation
            for operation in (
                hypothesis_operation,
                *admission_operations,
            )
            if operation is not None
        ]
        _persist_planner_operations(session, operations)
        result = commit_planner_operations(session, session_id=session_id, operations=operations)
        if result.failed_operation_ids:
            state.hard_stop_code = "execution_contract_commit_failed"
            state.hard_stop_message = "; ".join(result.errors.values())
            return state
        state.planner_operations.extend(operations)
        prepared.hypothesis_ref = state.bind_object_reference(
            "hypothesis", str(hypothesis.hypothesis_id)
        )
        prepared.execution_run_ref = state.bind_object_reference(
            "execution_run", str(execution_run.execution_run_id)
        )
        state.execution_admission = ExecutionAdmission(
            admitted=True,
            hypothesis_ref=prepared.hypothesis_ref,
            execution_run_ref=prepared.execution_run_ref,
        )
    except Exception as exc:
        session.rollback()
        state.hard_stop_code = "stale_execution_approval"
        state.hard_stop_message = str(exc)
        state.controlled_error = ControlledPlannerError(
            code=state.hard_stop_code,
            message=state.hard_stop_message,
        )
    finally:
        session.close()
    return state


@registry.register()
def manage_objective(state: State, runtime: Runtime[Context]) -> State:
    """Resolve current Objective state and draft an exact approval batch."""

    context = _runtime_context(runtime)
    if context is None or context.database_url is None:
        state.controlled_error = ControlledPlannerError(
            code="objective_store_unavailable",
            message="Objective management requires a configured planner database.",
        )
        return state

    session = get_session(context.database_url)
    try:
        repository = ObjectiveRepository(session)
        objectives = repository.list()
        active = repository.get_active()
        latest_frame = SessionFrameRepository(session).get_latest()
    except MultipleActiveObjectivesError as exc:
        state.controlled_error = ControlledPlannerError(
            code="multiple_active_objectives",
            message=str(exc),
        )
        return state
    finally:
        session.close()

    objective_by_ref = {
        state.bind_object_reference("objective", str(objective.objective_id)): objective
        for objective in objectives
    }
    has_existing_drafts = bool(
        state.objective_create_payloads or state.objective_update_payloads
    )
    if not has_existing_drafts:
        model = context.objective_management_model or _ConfiguredObjectiveManagementModel()
        try:
            draft_result = ObjectiveManagementDraft.model_validate(
                model.draft(
                    _objective_management_prompt(
                        state.request_understanding.request_text
                        if state.request_understanding is not None
                        else state.query,
                        active=active,
                        objective_by_ref=objective_by_ref,
                    )
                )
            )
            state.objective_update_payloads.extend(draft_result.objective_update_payloads)
            state.objective_create_payloads.extend(draft_result.objective_create_payloads)
        except Exception:
            state.controlled_error = ControlledPlannerError(
                code="objective_proposal_unavailable",
                message="Unable to produce a valid Objective lifecycle proposal.",
            )
            return state

    session_id = _session_id(state, runtime)
    operations: list[PlannerOperation] = []
    projected = {objective.objective_id: objective for objective in objectives}
    last_changed: Objective | None = None
    try:
        # Updates precede creation so an approved replacement archives/completes
        # the current Objective before the new ACTIVE row is inserted.
        for update_draft in state.objective_update_payloads:
            objective = objective_by_ref[update_draft.objective_ref]
            update_payload = update_draft.operation_payload(
                objective_id=objective.objective_id,
                expected_updated_at=objective.updated_at,
            )
            operations.append(
                PlannerOperation(
                    session_id=session_id,
                    operation_type=PlannerOperationType.UPDATE_OBJECTIVE,
                    payload=update_payload.model_dump(mode="json", exclude_unset=True),
                    produced_by_node=PlannerNodeName.MANAGE_OBJECTIVE,
                )
            )
            update_values = update_draft.model_dump(
                exclude={"objective_ref", "revision_reason", "user_decision_id"},
                exclude_none=True,
            )
            last_changed = objective.model_copy(update=update_values)
            projected[objective.objective_id] = last_changed

        for create_draft in state.objective_create_payloads:
            if create_draft.status != ObjectiveStatus.ACTIVE:
                raise ValueError("Public Objective creation must be ACTIVE.")
            objective_id = uuid4()
            create_payload = create_draft.operation_payload(objective_id=objective_id)
            operations.append(
                PlannerOperation(
                    session_id=session_id,
                    operation_type=PlannerOperationType.CREATE_OBJECTIVE,
                    payload=create_payload.model_dump(mode="json"),
                    produced_by_node=PlannerNodeName.MANAGE_OBJECTIVE,
                )
            )
            last_changed = Objective(**create_payload.model_dump())
            projected[objective_id] = last_changed
    except (KeyError, ValueError):
        state.controlled_error = ControlledPlannerError(
            code="invalid_objective_proposal",
            message="The Objective proposal contains an invalid lifecycle or local reference.",
        )
        return state

    if not operations or last_changed is None:
        state.controlled_error = ControlledPlannerError(
            code="empty_objective_proposal",
            message="The Objective request did not produce a lifecycle change.",
        )
        return state

    projected_active = [
        objective for objective in projected.values() if objective.status == ObjectiveStatus.ACTIVE
    ]
    if len(projected_active) > 1:
        state.controlled_error = ControlledPlannerError(
            code="multiple_active_objective_proposal",
            message="The proposal would leave more than one ACTIVE Objective.",
        )
        return state
    frame_objective = projected_active[0] if projected_active else last_changed
    frame = _successor_objective_frame(latest_frame, frame_objective)
    operations.append(
        PlannerOperation(
            session_id=session_id,
            operation_type=PlannerOperationType.UPDATE_SESSION_FRAME,
            payload=frame.model_dump(mode="json"),
            produced_by_node=PlannerNodeName.MANAGE_OBJECTIVE,
        )
    )
    state.active_session_frame_id = frame.session_frame_id
    state.planner_operations.extend(operations)
    return state


class ObjectiveManagementDraft(BaseModel):
    """Typed model output for governed Objective creation and mutation."""

    model_config = ConfigDict(extra="forbid")

    objective_update_payloads: list[ObjectiveUpdateDraft] = Field(default_factory=list)
    objective_create_payloads: list[ObjectiveCreateDraft] = Field(default_factory=list)


class _ConfiguredObjectiveManagementModel:
    """Adapter over the repository LLM factory for Objective proposals."""

    def __init__(self) -> None:
        from agents.llm import ModelConfig, create_agent

        self._agent = create_agent(
            worker="planner",
            config=ModelConfig(),
            deps_type=type(None),
            builtin_tools=[],
        )

    def draft(self, prompt: str) -> ObjectiveManagementDraft:
        result = self._agent.run_sync(prompt, output_type=ObjectiveManagementDraft)
        return ObjectiveManagementDraft.model_validate(result.output)


def _objective_management_prompt(
    query: str,
    *,
    active: Objective | None,
    objective_by_ref: dict[str, Objective],
) -> str:
    """Give the model local references and lifecycle semantics, never UUIDs."""

    inventory = [
        {
            "reference": reference,
            "title": objective.title,
            "statement": objective.statement,
            "status": objective.status.value,
        }
        for reference, objective in objective_by_ref.items()
    ]
    active_ref = next(
        (
            reference
            for reference, objective in objective_by_ref.items()
            if active is not None and objective.objective_id == active.objective_id
        ),
        None,
    )
    return (
        "Translate the user's Objective request into ObjectiveManagementDraft. "
        "Use only the supplied local references; never invent UUIDs. Every update requires "
        "a concrete revision_reason. ACTIVE is the singular current research intent. "
        "COMPLETED means explicit user acceptance of completion; ARCHIVED does not claim "
        "success. To switch, update the current Objective away from ACTIVE and then create "
        "or reactivate exactly one Objective. Do not mutate Tasks, Hypotheses, Evidence, or "
        "Discoveries.\n"
        f"Current ACTIVE reference: {active_ref}\n"
        f"Objective inventory: {json.dumps(inventory)}\n"
        f"Latest raw user request:\n{query}"
    )


def _successor_objective_frame(
    latest_frame: SessionFrame | None,
    objective: Objective,
) -> SessionFrame:
    """Build the successor frame included in the exact approved operation batch."""

    summary = (
        None
        if objective.status == ObjectiveStatus.ACTIVE
        else f"Objective is {objective.status.value}: {objective.title}"
    )
    if latest_frame is None:
        return SessionFrame(
            frame_topic=objective.title,
            objective_snapshot=objective.statement,
            objective_summary=summary,
        )
    return latest_frame.model_copy(
        update={
            "session_frame_id": uuid4(),
            "parent_session_frame_id": latest_frame.session_frame_id,
            "frame_topic": objective.title,
            "objective_snapshot": objective.statement,
            "objective_summary": summary,
        }
    )


@registry.register()
def manage_assumptions(state: State, runtime: Runtime[Context]) -> State:
    """Draft Assumption operations without using Assumptions as inference premises."""
    session_id = _session_id(state, runtime)
    for assumption in state.assumption_create_payloads:
        state.planner_operations.append(
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.CREATE_ASSUMPTION,
                payload=assumption.model_dump(mode="json"),
                produced_by_node=PlannerNodeName.MANAGE_ASSUMPTIONS,
            )
        )
    for draft in state.assumption_state_update_payloads:
        contradicted_by_discovery_ids = (
            [
                UUID(state.resolve_object_reference(discovery_ref))
                for discovery_ref in draft.contradicted_by_discovery_refs
            ]
            if draft.contradicted_by_discovery_refs is not None
            else None
        )
        replacement_assumption_id = (
            UUID(state.resolve_object_reference(draft.replacement_assumption_ref))
            if draft.replacement_assumption_ref is not None
            else None
        )
        state.planner_operations.append(
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.UPDATE_ASSUMPTION_STATE,
                payload=draft.operation_payload(
                    assumption_id=UUID(state.resolve_object_reference(draft.assumption_ref)),
                    contradicted_by_discovery_ids=contradicted_by_discovery_ids,
                    replacement_assumption_id=replacement_assumption_id,
                ).model_dump(
                    mode="json",
                    exclude_unset=True,
                ),
                produced_by_node=PlannerNodeName.MANAGE_ASSUMPTIONS,
            )
        )
    return state


# --------------------
# User interaction
# --------------------


@registry.register()
def review_result(state: State, runtime: Runtime[Context]) -> State:
    """Review a persisted analytical result with the user."""

    # TODO: Implement user-facing result review.
    return state


@registry.register()
def review_conflict(state: State, runtime: Runtime[Context]) -> State:
    """Review a persisted analytical conflict with the user."""

    # TODO: Implement user-facing conflict review.
    return state


@registry.register()
def request_user_input(state: State, runtime: Runtime[Context]) -> State:
    """Durably persist the approval request before exposing it to a caller."""

    context = _runtime_context(runtime)
    prepared = state.prepared_execution
    if (
        prepared is not None
        and state.execution_preparation is not None
        and state.execution_preparation.prepared
    ):
        if context is None or context.database_url is None:
            state.controlled_error = ControlledPlannerError(
                code="execution_store_unavailable",
                message="Execution approval requires a configured planner database.",
            )
            return state
        try:
            task_id = UUID(state.resolve_object_reference(prepared.task_ref))
            profile_id = UUID(state.resolve_object_reference(prepared.data_profile_ref))
            hypothesis_id = (
                UUID(state.resolve_object_reference(prepared.hypothesis_ref))
                if prepared.hypothesis_ref is not None
                else None
            )
        except ValueError as exc:
            state.controlled_error = ControlledPlannerError(
                code="unknown_execution_reference", message=str(exc)
            )
            return state

        session_id = _session_id(state, runtime) or "default"
        session = get_session(context.database_url)
        try:
            approvals = ExecutionApprovalRepository(session)
            approval = approvals.find_pending(
                session_id=session_id,
                task_id=task_id,
                contract_fingerprint=prepared.contract_fingerprint,
            )
            if approval is None:
                approval = approvals.create(
                    ExecutionApproval(
                        session_id=session_id,
                        task_id=task_id,
                        profile_id=profile_id,
                        hypothesis_id=hypothesis_id,
                        execution_ref=prepared.execution_ref,
                        contract_fingerprint=prepared.contract_fingerprint,
                        prepared_payload=_prepared_payload(prepared),
                    )
                )
        finally:
            session.close()

        state.pending_interaction = PendingUserInteraction(
            kind="execution_approval",
            payload={
                "execution_approval_id": str(approval.execution_approval_id),
                "execution_ref": prepared.execution_ref,
                "contract_fingerprint": prepared.contract_fingerprint,
                "task_id": str(task_id),
                "data_profile_id": str(profile_id),
            },
            allowed_actions=["approve", "cancel", "revise", "clarify"],
            snapshot_hash=prepared.contract_fingerprint,
            proposal_id=str(approval.execution_approval_id),
        )
        return state

    if state.planner_operations:
        operation_ids = [str(operation.operation_id) for operation in state.planner_operations]
        snapshot_hash = _planner_operations_fingerprint(state.planner_operations)
        if context is not None and context.database_url is not None:
            session = get_session(context.database_url)
            try:
                _persist_planner_operations(session, state.planner_operations)
                session.commit()
            finally:
                session.close()
        state.pending_interaction = PendingUserInteraction(
            kind="planner_operation_approval",
            payload={"operation_count": len(state.planner_operations)},
            allowed_actions=["approve", "cancel", "revise", "clarify"],
            operation_ids=operation_ids,
            snapshot_hash=snapshot_hash,
            proposal_id=snapshot_hash,
        )
    return state


@registry.register()
def resume_execution(state: State, runtime: Runtime[Context]) -> State:
    """Reconstruct one pending approval from the durable workflow record."""

    approval_id = state.resume_approval_id
    context = _runtime_context(runtime)
    if approval_id is None or context is None or context.database_url is None:
        state.controlled_error = ControlledPlannerError(
            code="execution_resume_unavailable",
            message="No durable execution approval is available to resume.",
        )
        return state
    session = get_session(context.database_url)
    try:
        approval = ExecutionApprovalRepository(session).get_by_id(approval_id)
    finally:
        session.close()
    if approval is None or approval.session_id != (_session_id(state, runtime) or "default"):
        state.controlled_error = ControlledPlannerError(
            code="invalid_execution_approval",
            message="The requested execution approval does not belong to this session.",
        )
        return state
    if approval.status not in {ExecutionApprovalStatus.PENDING, ExecutionApprovalStatus.APPROVED}:
        state.controlled_error = ControlledPlannerError(
            code="execution_approval_not_pending",
            message="The requested execution approval is no longer resumable.",
        )
        return state

    task_ref = state.bind_object_reference("task", str(approval.task_id))
    profile_ref = state.bind_object_reference("data_profile", str(approval.profile_id))
    hypothesis_ref = (
        state.bind_object_reference("hypothesis", str(approval.hypothesis_id))
        if approval.hypothesis_id is not None
        else None
    )
    prepared_payload = dict(approval.prepared_payload)
    prepared_payload.update(
        {
            "task_ref": task_ref,
            "data_profile_ref": profile_ref,
            "hypothesis_ref": hypothesis_ref,
            "execution_ref": approval.execution_ref,
            "contract_fingerprint": approval.contract_fingerprint,
        }
    )
    state.prepared_execution = PreparedExecution.model_validate(prepared_payload)
    state.execution_preparation = ExecutionPreparation(prepared=True)
    state.task_selection = TaskSelection(task_ref=task_ref, selected=True)
    state.pending_interaction = PendingUserInteraction(
        kind="execution_approval",
        payload={
            "execution_approval_id": str(approval.execution_approval_id),
            "execution_ref": approval.execution_ref,
            "contract_fingerprint": approval.contract_fingerprint,
            "task_id": str(approval.task_id),
            "data_profile_id": str(approval.profile_id),
        },
        allowed_actions=["approve", "cancel", "revise", "clarify"],
        snapshot_hash=approval.contract_fingerprint,
        proposal_id=str(approval.execution_approval_id),
    )
    return state


@registry.register()
def resume_planner_operations(state: State, runtime: Runtime[Context]) -> State:
    """Reload one pending, session-bound PlannerOperation proposal for a user decision."""

    context = _runtime_context(runtime)
    session_id = _session_id(state, runtime)
    requested_ids = state.resume_operation_ids
    if context is None or context.database_url is None or session_id is None or not requested_ids:
        state.controlled_error = ControlledPlannerError(
            code="planner_operation_resume_unavailable",
            message="A proposal decision must include its durable operation identifiers.",
        )
        return state
    if len(requested_ids) != len(set(requested_ids)):
        state.controlled_error = ControlledPlannerError(
            code="invalid_planner_operation_proposal",
            message="The proposal contains duplicate operation identifiers.",
        )
        return state

    session = get_session(context.database_url)
    try:
        repository = PlannerOperationRepository(session)
        operations = [repository.get_by_id(operation_id) for operation_id in requested_ids]
    finally:
        session.close()
    if (
        any(operation is None for operation in operations)
        or any(
            operation.session_id != session_id for operation in operations if operation is not None
        )
        or any(
            operation.approval_state != PlannerOperationApprovalState.PENDING
            for operation in operations
            if operation is not None
        )
    ):
        state.controlled_error = ControlledPlannerError(
            code="invalid_planner_operation_proposal",
            message=(
                "The proposal is unknown, belongs to another session, or is no longer pending."
            ),
        )
        return state

    restored_operations = [operation for operation in operations if operation is not None]
    snapshot_hash = _planner_operations_fingerprint(restored_operations)
    state.planner_operations = restored_operations
    state.operation_ids_to_commit = [str(operation_id) for operation_id in requested_ids]
    frame_operations = [
        operation
        for operation in restored_operations
        if operation.operation_type == PlannerOperationType.UPDATE_SESSION_FRAME
    ]
    if len(frame_operations) == 1 and frame_operations[0].payload.get("session_frame_id"):
        state.active_session_frame_id = UUID(
            str(frame_operations[0].payload["session_frame_id"])
        )
    state.pending_interaction = PendingUserInteraction(
        kind="planner_operation_approval",
        payload={"operation_count": len(restored_operations)},
        allowed_actions=["approve", "cancel", "revise", "clarify"],
        operation_ids=state.operation_ids_to_commit,
        snapshot_hash=snapshot_hash,
        proposal_id=snapshot_hash,
    )
    return state


@registry.register()
def pause(state: State, runtime: Runtime[Context]) -> State:
    """Pause the current process and wait for user input or confirmation."""

    # TODO: Implement durable pause handling beyond the graph interrupt boundary.
    pass


@registry.register()
def process_decision(state: State, runtime: Runtime[Context]) -> State:
    """Validate a user decision; routing is deliberately separate from state updates."""

    interaction = state.pending_interaction
    decision = state.planner_decision
    if interaction is None or decision is None:
        state.interaction_error = "No user approval was supplied for the pending interaction."
        return state
    if interaction.kind == "planner_operation_approval":
        return _process_planner_operation_decision(state, runtime)
    context = _runtime_context(runtime)
    if context is None or context.database_url is None:
        state.interaction_error = "Execution approval requires a configured planner database."
        return state
    approval_id_text = interaction.payload.get("execution_approval_id")
    try:
        approval_id = UUID(str(approval_id_text))
    except (TypeError, ValueError):
        state.interaction_error = "The pending execution approval is malformed."
        return state
    session = get_session(context.database_url)
    try:
        approvals = ExecutionApprovalRepository(session)
        approval = approvals.get_by_id(approval_id)
        if approval is None or approval.session_id != (_session_id(state, runtime) or "default"):
            state.execution_revalidation = ExecutionRevalidation(
                valid=False,
                error_code="invalid_execution_approval",
                error_message="The approval does not belong to this planner session.",
            )
            return state
        if decision.action != "approve":
            approvals.set_status(approval_id, ExecutionApprovalStatus.CANCELLED)
            return state
        if approval.status == ExecutionApprovalStatus.CONSUMED:
            state.execution_revalidation = ExecutionRevalidation(
                valid=False,
                error_code="execution_already_admitted",
                error_message="This approval has already admitted an execution attempt.",
            )
            return state
        if approval.status != ExecutionApprovalStatus.PENDING:
            state.execution_revalidation = ExecutionRevalidation(
                valid=False,
                error_code="execution_approval_not_pending",
                error_message="This execution approval is no longer pending.",
            )
            return state
        # A legacy in-process caller may omit proposal_id, but cannot supply a
        # different id or fingerprint to authorize another contract.
        if decision.proposal_id is not None and decision.proposal_id != str(approval_id):
            state.execution_revalidation = ExecutionRevalidation(
                valid=False,
                error_code="stale_execution_approval",
                error_message="The approval does not identify the pending execution contract.",
            )
            return state
        approvals.set_status(approval_id, ExecutionApprovalStatus.APPROVED)
    finally:
        session.close()

    if decision.action != "approve":
        return state

    if interaction.kind != "execution_approval" or state.prepared_execution is None:
        state.interaction_error = "The pending interaction is not an execution approval."
        return state
    prepared = state.prepared_execution
    if (
        approval.contract_fingerprint != prepared.contract_fingerprint
        or interaction.snapshot_hash != prepared.contract_fingerprint
        or interaction.payload.get("execution_ref") != prepared.execution_ref
        or (decision.execution_ref is not None and decision.execution_ref != prepared.execution_ref)
    ):
        state.execution_revalidation = ExecutionRevalidation(
            valid=False,
            error_code="stale_execution_approval",
            error_message="The approved execution contract no longer matches the current plan.",
        )
        return state
    state.execution_revalidation = ExecutionRevalidation(valid=True)
    return state


def _process_planner_operation_decision(
    state: State,
    runtime: Runtime[Context],
) -> State:
    """Bind a decision to exactly the persisted task-operation proposal it reviews."""

    interaction = state.pending_interaction
    decision = state.planner_decision
    assert interaction is not None
    assert decision is not None
    expected_ids = interaction.operation_ids
    if (
        not interaction.proposal_id
        or decision.proposal_id != interaction.proposal_id
        or decision.selected_ids != expected_ids
    ):
        state.interaction_error = "The decision does not match the pending proposal."
        return state
    approval_state = (
        PlannerOperationApprovalState.APPROVED
        if decision.action == "approve"
        else PlannerOperationApprovalState.REJECTED
    )
    for operation in state.planner_operations:
        operation.approval_state = approval_state

    context = _runtime_context(runtime)
    if context is not None and context.database_url is not None:
        session = get_session(context.database_url)
        try:
            for operation in state.planner_operations:
                record = session.get(PlannerOperationRecord, operation.operation_id)
                if record is not None:
                    record.approval_state = approval_state
                    session.add(record)
            session.commit()
        finally:
            session.close()
    return state


def route_process_decision(state: State, runtime: Runtime[Context]) -> str:
    """Route only after the decision node has recorded its validation result."""

    if state.execution_revalidation is not None and state.execution_revalidation.valid:
        return "approved_execution"
    if (
        state.pending_interaction is not None
        and state.pending_interaction.kind == "planner_operation_approval"
    ):
        if state.planner_decision is not None and state.planner_decision.action == "approve":
            return "approved_task"
    if state.planner_decision is not None and state.planner_decision.action == "clarify":
        return "clarify"
    return "cancel"


# --------------------
# Finalization
# --------------------


@registry.register()
def commit(state: State, runtime: Runtime[Context]) -> State:
    """
    Persist approved planner operations at the commit boundary.

    Future work will make approval, transaction, and rollback behavior explicit
    here. Planner nodes must keep producing operations rather than mutating FCOs.
    """
    context = _runtime_context(runtime)
    if context is None or context.database_url is None:
        return state

    session = get_session(context.database_url)
    try:
        _persist_planner_operations(session, state.planner_operations)
        if state.operation_ids_to_commit is not None:
            operation_ids = [UUID(operation_id) for operation_id in state.operation_ids_to_commit]
            state.commit_result = commit_planner_operations(
                session,
                session_id=context.session_id or state.session_id,
                operation_ids=operation_ids,
            )
        else:
            state.commit_result = commit_planner_operations(
                session,
                operations=state.planner_operations,
                session_id=context.session_id or state.session_id,
            )
    finally:
        session.close()
    return state


def _runtime_context(runtime: Runtime[Context] | None) -> Context | None:
    return getattr(runtime, "context", None)


def _read_session(runtime: Runtime[Context] | None) -> Session | None:
    """Open a short-lived read session only when planner execution is configured."""

    context = _runtime_context(runtime)
    if context is None or context.database_url is None:
        return None
    return get_session(context.database_url)


def _execution_not_prepared(
    state: State,
    error_code: str,
    error_message: str,
) -> State:
    state.execution_preparation = ExecutionPreparation(
        prepared=False,
        error_code=error_code,
        error_message=error_message,
    )
    return state


def _execution_contract_fingerprint(task: Any, profile: Any, specification: Any) -> str:
    """Bind approval to the exact task, profile, method, variables, and parameters."""

    payload = {
        "task_id": str(task.task_id),
        "task_updated_at": task.updated_at.isoformat(),
        "profile_id": str(profile.profile_id),
        "profile_version_at": getattr(profile, "updated_at", profile.created_at).isoformat(),
        "profile_lifecycle_state": profile.lifecycle_state.value,
        "profile_accepted": profile.accepted_as_ground_truth,
        "variables": specification.variable_bindings,
        "scope": specification.scope,
        "method": specification.validation_method,
        "parameters": [
            parameter.model_dump(mode="json") for parameter in specification.method_parameters
        ],
        "decision_rule": (
            specification.decision_rule.model_dump(mode="json")
            if hasattr(specification.decision_rule, "model_dump")
            else specification.decision_rule
        ),
    }
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _prepared_payload(prepared: PreparedExecution) -> dict[str, Any]:
    """Serialize only durable contract content; local handles are reconstructed on resume."""

    return {
        "task_title": prepared.task_title,
        "dataset_path": prepared.dataset_path,
        "hypothesis": prepared.hypothesis.model_dump(mode="json"),
        "specification": prepared.specification.model_dump(mode="json"),
        "deterministic_seed": prepared.deterministic_seed,
    }


def _session_id(state: State, runtime: Runtime[Context] | None) -> str | None:
    context = _runtime_context(runtime)
    if context is not None and context.session_id is not None:
        return context.session_id
    return state.session_id


def _persist_planner_operations(
    session: Session,
    operations: list[PlannerOperation],
) -> None:
    repository = PlannerOperationRepository(session)
    for operation in operations:
        if repository.get_by_id(operation.operation_id) is None:
            repository.stage_create(operation)


def _planner_operations_fingerprint(operations: list[PlannerOperation]) -> str:
    """Fingerprint the exact ordered proposal the user is being asked to approve."""

    content = [
        {
            "operation_id": str(operation.operation_id),
            "operation_type": operation.operation_type,
            "payload": operation.payload,
            "session_id": operation.session_id,
        }
        for operation in operations
    ]
    return sha256(json.dumps(content, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
