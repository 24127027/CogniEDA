from application.orchestrator.planner_commit import commit_planner_operations
from db.session import get_session
from langgraph.runtime import Runtime
from repositories import PlannerOperationRepository
from schemas.enums import PlannerNodeName, PlannerOperationType
from schemas.planner_operations import PlannerOperation
from sqlmodel import Session

from ..utilities.nodes_registry import NodeRegistry
from .types import Context, State

registry = NodeRegistry[State, Context]()
R = registry.R

# --------------------
# Core
# --------------------


@registry.register()
def understand_request(state: State, runtime: Runtime[Context]) -> None:
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
def answer_question(state: State, runtime: Runtime[Context]) -> None:
    """LLM answers the user's question

    The LLM is provided with context from the session, so it can answer the question more
    accurately.
    """
    pass


# --------------------
# Research planning
# --------------------


@registry.register()
def propose_questions(state: State, runtime: Runtime[Context]) -> None:
    """
    LLM proposes possible research directions, open questions, or
    investigation ideas based on the current research context.
    """
    pass


@registry.register()
def expand_plan(state: State, runtime: Runtime[Context]) -> None:
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
def manage_tasks(state: State, runtime: Runtime[Context]) -> State:
    """
    Draft Task operations without directly mutating persistent Task records.

    Later workflow code can decide which operations require user approval before
    commit applies them.
    """
    session_id = _session_id(state, runtime)
    for task in state.task_create_payloads:
        state.planner_operations.append(
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.CREATE_TASK,
                payload=task.model_dump(mode="json"),
                produced_by_node=PlannerNodeName.MANAGE_TASKS,
            )
        )
    for task_update in state.task_update_payloads:
        state.planner_operations.append(
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.UPDATE_TASK,
                payload=task_update.operation_payload().model_dump(
                    mode="json",
                    exclude_unset=True,
                ),
                produced_by_node=PlannerNodeName.MANAGE_TASKS,
            )
        )
    for task_state_change in state.task_state_change_payloads:
        state.planner_operations.append(
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.CHANGE_TASK_STATE,
                payload=task_state_change.operation_payload().model_dump(
                    mode="json",
                    exclude_unset=True,
                ),
                produced_by_node=PlannerNodeName.MANAGE_TASKS,
            )
        )
    return state


@registry.register()
def select_task(state: State, runtime: Runtime[Context]) -> None:
    """
    Determine which task to execute 
    Planner resolves which Task object this refers to.
    """
    pass


# --------------------
# Execution
# --------------------


@registry.register()
def prepare_execution(state: State, runtime: Runtime[Context]) -> None:
    """ 
    Compile an active terminal analytical Task into execution context.

    Later runtime work will prepare the single Hypothesis associated with the
    selected terminal Task. This skeleton does not execute or mutate state.
    """
    pass


@registry.register()
def dispatch_executor(state: State, runtime: Runtime[Context]) -> None:
    """Placeholder for delegating to an executor agent."""
    pass


@registry.register()
def review_execution(state: State, runtime: Runtime[Context]) -> None:
    """Review executor results.

    Later implementation will produce Evidence and Discovery operations from
    executor output. This skeleton does not synthesize discoveries.
    """
    pass


# --------------------
# Knowledge management
# --------------------


@registry.register()
def review_conflicts(state: State, runtime: Runtime[Context]) -> State:
    """Draft review flags when Discoveries contradict Assumptions.

    Flagging is a user-review signal; it does not rewrite Assumption truth.
    """
    session_id = _session_id(state, runtime)
    for draft in state.conflict_flag_payloads:
        state.planner_operations.append(
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.FLAG_OBJECT,
                payload=draft.operation_payload().model_dump(
                    mode="json",
                    exclude_unset=True,
                ),
                produced_by_node=PlannerNodeName.REVIEW_CONFLICTS,
            )
        )
    return state


@registry.register()
def manage_objective(state: State, runtime: Runtime[Context]) -> State:
    """Draft Objective update operations without mutating the Objective directly."""
    session_id = _session_id(state, runtime)
    for draft in state.objective_update_payloads:
        state.planner_operations.append(
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.UPDATE_OBJECTIVE,
                payload=draft.operation_payload().model_dump(
                    mode="json",
                    exclude_unset=True,
                ),
                produced_by_node=PlannerNodeName.MANAGE_OBJECTIVE,
            )
        )
    return state


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
        state.planner_operations.append(
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.UPDATE_ASSUMPTION_STATE,
                payload=draft.operation_payload().model_dump(
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
def request_user_input(state: State, runtime: Runtime[Context]) -> None:
    """Prepare a request for clarification or other user input."""
    pass


@registry.register()
def pause(state: State, runtime: Runtime[Context]) -> None:
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
            state.commit_result = commit_planner_operations(
                session,
                session_id=context.session_id or state.session_id,
                operation_ids=state.operation_ids_to_commit,
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
