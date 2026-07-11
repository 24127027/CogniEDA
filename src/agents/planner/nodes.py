from langgraph.runtime import Runtime
from sqlmodel import Session

from application.orchestrator.planner_commit import commit_planner_operations
from db.session import get_session
from repositories import PlannerOperationRepository
from schemas.enums import PlannerNodeName, PlannerOperationType
from schemas.planner_operations import PlannerOperation

from ..utilities.nodes_registry import NodeRegistry
from .types import Context, State

registry = NodeRegistry[State, Context]()
R = registry.R

# --------------------
# Core
# --------------------


@registry.register()
def understand_request(state: State, runtime: Runtime[Context]):
    """
    LLM interprets the user's latest message.

    The model identifies the user's intent and extracts any information
    needed for subsequent planning. This step intentionally does not
    consume Session Frame context so intent recognition is based solely
    on the user's request.
    """
    pass


@registry.register()
def route_intent(state: State, runtime: Runtime[Context]) -> str:
    """Route the user's intent to the appropriate node and return a routing key."""
    raise NotImplementedError(
        "route_intent must return one of: answer, suggest, manage_task, execute, "
        "objective, assumption."
    )


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

@registry.register()
def manage_tasks(state: State, runtime: Runtime[Context]):
    """
    Apply user-authorized modifications to the Task hierarchy.

    Supported operations include creating, updating, deleting,
    and changing Task state.

    Should produce operations that later apply to the Task hierarchy, but does not directly
    modify it.
    """
    session_id = _session_id(state, runtime)
    for task in state.task_create_payloads:
        state.planner_operations.append(
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.CREATE_TASK,
                target_object_id=task.task_id,
                target_object_type="task",
                payload=task.model_dump(mode="json"),
                produced_by_node=PlannerNodeName.MANAGE_TASKS,
            )
        )
    for draft in state.task_update_payloads:
        state.planner_operations.append(
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.UPDATE_TASK,
                target_object_id=draft.require_target_object_id(),
                target_object_type="task",
                payload=draft.operation_payload(),
                produced_by_node=PlannerNodeName.MANAGE_TASKS,
            )
        )
    for draft in state.task_state_change_payloads:
        state.planner_operations.append(
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.CHANGE_TASK_STATE,
                target_object_id=draft.require_target_object_id(),
                target_object_type="task",
                payload=draft.operation_payload(),
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
def request_user_input(state: State, runtime: Runtime[Context]):
    """Prepare a request for clarification or other user input."""
    pass


@registry.register()
def pause(state: State, runtime: Runtime[Context]):
    """Pause the current process and wait for user input or confirmation before proceeding."""

    pass


@registry.register()
def process_decision(state: State, runtime: Runtime[Context]) -> str:
    """Interpret the user's response after a pause and return a routing key for the planner."""
    raise NotImplementedError(
        "process_decision must return one of: clarify, approved_questions, "
        "approved_task, approved_plan, approved_conflict, approved_execution, cancel."
    )


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
    if context is None or context.database_url is None:
        return state

    session = get_session(context.database_url)
    try:
        _persist_planner_operations(session, state.planner_operations)
        operation_ids = state.operation_ids_to_commit
        if operation_ids is None and state.planner_operations:
            operation_ids = [
                operation.operation_id for operation in state.planner_operations
            ]
        state.commit_result = commit_planner_operations(
            session,
            session_id=context.session_id or state.session_id,
            operation_ids=operation_ids,
        )
    finally:
        session.close()
    return state


def _runtime_context(runtime: Runtime[Context] | None) -> Context | None:
    return getattr(runtime, "context", None)


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
            repository.create(operation)
