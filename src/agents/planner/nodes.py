import json
from hashlib import sha256

from langgraph.runtime import Runtime
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlmodel import Session

from application.orchestrator.planner_commit import commit_planner_operations
from db.session import get_session
from repositories import PlannerOperationRepository
from schemas.enums import (
    PlannerNodeName,
    PlannerOperationApprovalState,
    PlannerOperationType,
)
from schemas.planner_operations import PlannerOperation

from ..utilities.nodes_registry import NodeRegistry
from .types import (
    COMMAND_TO_INTENT,
    Context,
    ControlledPlannerError,
    PendingUserInteraction,
    RequestUnderstanding,
    RequestUnderstandingModel,
    State,
    TaskCreateDraft,
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
    """Build the isolated prompt used to classify only the newest request."""

    intent_definitions = "\n".join(
        f"- {intent}: classify requests that should be routed to {intent}."
        for intent in COMMAND_TO_INTENT.values()
    )
    return (
        "Classify only the latest raw user request into one allowed planner intent.\n"
        "Return structured output with `intent` and `request_text`.\n"
        "Do not invent IDs, Assumptions, Evidence, Discoveries, or project state. "
        "Do not use prior conversation or SessionFrame context.\n"
        f"Allowed intents:\n{intent_definitions}\n\n"
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
    """Classify the latest request without exposing history to the classifier."""

    command = parse_explicit_command(state.query)
    if command is not None:
        intent = COMMAND_TO_INTENT.get(command.command)
        state.request_understanding = (
            RequestUnderstanding(
                intent=intent,
                request_text=command.request_text,
                source="explicit_command",
                explicit_command=command.command,
            )
            if intent is not None
            else _invalid_command_understanding(
                command.original_command,
                command.request_text,
            )
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
    except (TypeError, ValueError, ValidationError, RuntimeError):
        state.request_understanding = _invalid_llm_understanding(state.query)
    return state


def route_entry(state: State, runtime: Runtime[Context]) -> str:
    """Start a fresh request or reload the durable proposal selected by a decision."""

    return "resume_planner_operations" if state.resume_requested else "understand_request"


def route_intent(state: State, runtime: Runtime[Context]) -> str:
    """Route only a valid request-understanding result."""

    understanding = state.request_understanding
    if (
        understanding is None
        or understanding.requires_user_correction
        or understanding.intent is None
    ):
        return "invalid_request"
    return understanding.intent


@registry.register()
def invalid_request(state: State, runtime: Runtime[Context]) -> State:
    """Terminate unsupported or unclassifiable requests without mutations."""

    return state


# --------------------
# Question answering
# --------------------


@registry.register()
def answer_question(state: State, runtime: Runtime[Context]):
    """LLM answers the user's question

    The LLM is provided with context from the session, so it can answer the question more
    accurately.
    """
    pass


# --------------------
# Research planning
# --------------------


@registry.register()
def propose_questions(state: State, runtime: Runtime[Context]):
    """
    LLM proposes possible research directions, open questions, or
    investigation ideas based on the current research context.
    """
    pass


@registry.register()
def expand_plan(state: State, runtime: Runtime[Context]):
    """
    LLM expands an approved research direction into executable Tasks.

    This may include refining scope, decomposing large Tasks into
    subtasks, identifying dependencies, and determining a concrete
    execution plan.
    """
    pass


# --------------------
# Task management
# --------------------


class TaskManagementDraft(BaseModel):
    """Structured output for the narrow Task-creation proposal surface."""

    model_config = ConfigDict(extra="forbid")

    task_create_payloads: list[TaskCreateDraft] = Field(default_factory=list)


class _ConfiguredTaskManagementModel:
    """Adapter over the repository LLM factory for Task proposal drafting."""

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


def _task_management_prompt(query: str) -> str:
    """Build a proposal-only prompt that cannot supply durable Task identifiers."""

    return (
        "Translate the latest user request into one or more proposed new Tasks.\n"
        "Return only title, description, lifecycle_state, task_kind, variables, and "
        "evidence_expectation.\n"
        "Do not invent IDs or claim that any Task has been created. The caller must "
        "approve the resulting operation batch before persistence applies it.\n\n"
        f"Latest raw user request:\n{query}"
    )


@registry.register()
def manage_tasks(state: State, runtime: Runtime[Context]) -> State:
    """
    Produce Task operations without directly mutating durable Task records.

    This PR narrows model-authored output to creation drafts. Pre-existing typed
    update drafts remain accepted for the current scaffold but are not requested
    from the model on this surface.
    """
    if state.planner_operations:
        return state

    has_existing_drafts = any(
        (
            state.task_create_payloads,
            state.task_update_payloads,
            state.task_state_change_payloads,
        )
    )
    if not has_existing_drafts:
        context = _runtime_context(runtime)
        model = context.task_management_model if context is not None else None
        if model is None:
            model = _ConfiguredTaskManagementModel()
        try:
            management_draft = TaskManagementDraft.model_validate(
                model.draft(_task_management_prompt(state.query))
            )
        except (TypeError, ValueError, ValidationError, RuntimeError):
            state.controlled_error = ControlledPlannerError(
                code="task_proposal_unavailable",
                message="Unable to produce a valid Task proposal from the request.",
            )
            return state
        state.task_create_payloads.extend(management_draft.task_create_payloads)

    session_id = _session_id(state, runtime)
    for task in state.task_create_payloads:
        state.planner_operations.append(
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.CREATE_TASK,
                payload=task.operation_payload().model_dump(
                    mode="json",
                    exclude_none=True,
                ),
                produced_by_node=PlannerNodeName.MANAGE_TASKS,
            )
        )
    for task_update in state.task_update_payloads:
        state.planner_operations.append(
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.UPDATE_TASK,
                target_object_id=task_update.require_target_object_id(),
                target_object_type="task",
                payload=task_update.operation_payload(),
                produced_by_node=PlannerNodeName.MANAGE_TASKS,
            )
        )
    for task_state_change in state.task_state_change_payloads:
        state.planner_operations.append(
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.CHANGE_TASK_STATE,
                target_object_id=task_state_change.require_target_object_id(),
                target_object_type="task",
                payload=task_state_change.operation_payload(),
                produced_by_node=PlannerNodeName.MANAGE_TASKS,
            )
        )
    return state


@registry.register()
def select_task(state: State, runtime: Runtime[Context]):
    """
    Determine which task to execute 
    Planner resolves which Task object this refers to.
    """
    pass


# --------------------
# Execution
# --------------------


@registry.register()
def prepare_execution(state: State, runtime: Runtime[Context]):
    """ 
    Choose the appropriate executor for the task and prepare the execution context.
    """
    pass


@registry.register()
def dispatch_executor(state: State, runtime: Runtime[Context]):
    """Delegate to another specialist agent."""
    pass


@registry.register()
def review_execution(state: State, runtime: Runtime[Context]):
    """Review the results of the execution and update the state accordingly."""
    pass


# --------------------
# Knowledge management
# --------------------


@registry.register()
def review_conflicts(state: State, runtime: Runtime[Context]):
    """Determine whether new results contradict existing knowledge
    and prepare user review.
    """
    session_id = _session_id(state, runtime)
    for draft in state.conflict_flag_payloads:
        state.planner_operations.append(
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.FLAG_OBJECT,
                target_object_id=draft.require_target_object_id(),
                target_object_type=draft.target_object_type,
                payload=draft.operation_payload(),
                produced_by_node=PlannerNodeName.REVIEW_CONFLICTS,
            )
        )
    return state


@registry.register()
def manage_objective(state: State, runtime: Runtime[Context]):
    """Apply changes to the objective, such as updating, refining, or clarifying it."""
    session_id = _session_id(state, runtime)
    for draft in state.objective_update_payloads:
        state.planner_operations.append(
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.UPDATE_OBJECTIVE,
                target_object_id=draft.require_target_object_id(),
                target_object_type="objective",
                payload=draft.operation_payload(),
                produced_by_node=PlannerNodeName.MANAGE_OBJECTIVE,
            )
        )
    return state


@registry.register()
def manage_assumptions(state: State, runtime: Runtime[Context]):
    """Apply changes to the assumptions, such as updating, refining, or clarifying them."""
    session_id = _session_id(state, runtime)
    for assumption in state.assumption_create_payloads:
        state.planner_operations.append(
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.CREATE_ASSUMPTION,
                target_object_id=assumption.assumption_id,
                target_object_type="assumption",
                payload=assumption.model_dump(mode="json"),
                produced_by_node=PlannerNodeName.MANAGE_ASSUMPTIONS,
            )
        )
    for draft in state.assumption_state_update_payloads:
        state.planner_operations.append(
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.UPDATE_ASSUMPTION_STATE,
                target_object_id=draft.require_target_object_id(),
                target_object_type="assumption",
                payload=draft.operation_payload(),
                produced_by_node=PlannerNodeName.MANAGE_ASSUMPTIONS,
            )
        )
    return state


# --------------------
# User interaction
# --------------------


@registry.register()
def request_user_input(state: State, runtime: Runtime[Context]) -> State:
    """Persist the exact pending operation batch before requesting approval."""

    if not state.planner_operations or state.controlled_error is not None:
        return state

    context = _runtime_context(runtime)
    if context is None or context.database_url is None:
        state.controlled_error = ControlledPlannerError(
            code="planner_operation_store_unavailable",
            message="Task proposal approval requires a configured planner database.",
        )
        return state

    session = get_session(context.database_url)
    try:
        repository = PlannerOperationRepository(session)
        existing_operations = [
            repository.get_by_id(operation.operation_id)
            for operation in state.planner_operations
        ]
        if all(operation is None for operation in existing_operations):
            durable_operations = repository.create_batch(state.planner_operations)
        elif any(operation is None for operation in existing_operations):
            state.controlled_error = ControlledPlannerError(
                code="invalid_planner_operation_proposal",
                message="The Task proposal could not be persisted as one complete batch.",
            )
            return state
        elif any(
            operation.approval_state != PlannerOperationApprovalState.PENDING
            for operation in existing_operations
            if operation is not None
        ):
            state.controlled_error = ControlledPlannerError(
                code="invalid_planner_operation_proposal",
                message="The Task proposal is no longer pending approval.",
            )
            return state
        else:
            durable_operations = [
                operation for operation in existing_operations if operation is not None
            ]
    finally:
        session.close()

    state.planner_operations = durable_operations
    operation_ids = [str(operation.operation_id) for operation in durable_operations]
    snapshot_hash = _planner_operations_fingerprint(durable_operations)
    state.pending_interaction = PendingUserInteraction(
        kind="planner_operation_approval",
        payload={"operation_count": len(durable_operations)},
        allowed_actions=["approve", "cancel", "revise", "clarify"],
        operation_ids=operation_ids,
        snapshot_hash=snapshot_hash,
        proposal_id=snapshot_hash,
    )
    return state


@registry.register()
def resume_planner_operations(state: State, runtime: Runtime[Context]) -> State:
    """Reload one pending, session-bound operation batch before applying a decision."""

    context = _runtime_context(runtime)
    session_id = _session_id(state, runtime)
    requested_ids = state.resume_operation_ids
    if context is None or context.database_url is None or not requested_ids:
        state.controlled_error = ControlledPlannerError(
            code="planner_operation_resume_unavailable",
            message="A proposal decision must include its durable operation identifiers.",
        )
        return state
    if len(requested_ids) != len(set(requested_ids)):
        state.controlled_error = ControlledPlannerError(
            code="invalid_planner_operation_proposal",
            message="The Task proposal contains duplicate operation identifiers.",
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
            operation.session_id != session_id
            for operation in operations
            if operation is not None
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
                "The Task proposal is unknown, belongs to another session, or is no "
                "longer pending."
            ),
        )
        return state

    durable_operations = [operation for operation in operations if operation is not None]
    operation_ids = [str(operation_id) for operation_id in requested_ids]
    snapshot_hash = _planner_operations_fingerprint(durable_operations)
    state.planner_operations = durable_operations
    state.operation_ids_to_commit = requested_ids
    state.pending_interaction = PendingUserInteraction(
        kind="planner_operation_approval",
        payload={"operation_count": len(durable_operations)},
        allowed_actions=["approve", "cancel", "revise", "clarify"],
        operation_ids=operation_ids,
        snapshot_hash=snapshot_hash,
        proposal_id=snapshot_hash,
    )
    return state


@registry.register()
def pause(state: State, runtime: Runtime[Context]) -> State:
    """Pause the current process and wait for user input or confirmation before proceeding."""

    return state


@registry.register()
def process_decision(state: State, runtime: Runtime[Context]) -> State:
    """Bind a decision to the exact durable Task-operation proposal it reviews."""

    interaction = state.pending_interaction
    decision = state.planner_decision
    if decision is None:
        return state
    if interaction is None:
        state.interaction_error = "No Task proposal is awaiting a decision."
        return state
    if (
        decision.proposal_id != interaction.proposal_id
        or decision.selected_ids != interaction.operation_ids
    ):
        state.interaction_error = "The decision does not match the pending Task proposal."
        return state

    context = _runtime_context(runtime)
    if context is None or context.database_url is None:
        state.interaction_error = "Task proposal approval requires a configured planner database."
        return state

    approval_state = (
        PlannerOperationApprovalState.APPROVED
        if decision.action == "approve"
        else PlannerOperationApprovalState.REJECTED
    )
    session = get_session(context.database_url)
    try:
        repository = PlannerOperationRepository(session)
        state.planner_operations = repository.set_approval_state_batch(
            state.resume_operation_ids,
            expected_state=PlannerOperationApprovalState.PENDING,
            approval_state=approval_state,
        )
    except ValueError:
        state.controlled_error = ControlledPlannerError(
            code="invalid_planner_operation_proposal",
            message="The Task proposal is no longer available for this decision.",
        )
    finally:
        session.close()
    return state


def route_process_decision(state: State, runtime: Runtime[Context]) -> str:
    """Route after validating the decision without falling back to session-wide commit."""

    if state.controlled_error is not None or state.interaction_error is not None:
        return "end"
    if state.planner_decision is None:
        return "end"
    if state.planner_decision.action == "approve":
        return "approved_task"
    if state.planner_decision.action in {"cancel", "revise"}:
        return "cancel"
    return "end"


# --------------------
# Finalization
# --------------------


@registry.register()
def commit(state: State, runtime: Runtime[Context]):
    """
    Atomically persist all planner state changes.

    This includes updating Tasks, Objectives, Assumptions, Session Frame,
    and any other modified planner state before ending the iteration.
    """
    context = _runtime_context(runtime)
    if (
        context is None
        or context.database_url is None
        or state.controlled_error is not None
        or state.interaction_error is not None
        or not state.planner_operations
    ):
        return state

    operation_ids = state.operation_ids_to_commit or [
        operation.operation_id for operation in state.planner_operations
    ]
    if not operation_ids:
        return state

    session = get_session(context.database_url)
    try:
        _persist_planner_operations(session, state.planner_operations)
        state.commit_result = commit_planner_operations(
            session,
            session_id=_session_id(state, runtime),
            operation_ids=operation_ids,
        )
    finally:
        session.close()
    return state


def _runtime_context(runtime: Runtime[Context] | None) -> Context | None:
    return getattr(runtime, "context", None)


def _session_id(state: State, runtime: Runtime[Context] | None) -> str:
    context = _runtime_context(runtime)
    if context is not None and context.session_id is not None:
        return context.session_id
    return state.session_id or "default"


def _persist_planner_operations(
    session: Session,
    operations: list[PlannerOperation],
) -> None:
    repository = PlannerOperationRepository(session)
    missing_operations = [
        operation
        for operation in operations
        if repository.get_by_id(operation.operation_id) is None
    ]
    if missing_operations:
        repository.create_batch(missing_operations)


def _planner_operations_fingerprint(operations: list[PlannerOperation]) -> str:
    """Fingerprint the exact ordered proposal the user is being asked to approve."""

    content = [
        {
            "operation_id": str(operation.operation_id),
            "operation_type": operation.operation_type.value,
            "payload": operation.payload,
            "session_id": operation.session_id,
        }
        for operation in operations
    ]
    return sha256(
        json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
