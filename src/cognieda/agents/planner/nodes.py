from __future__ import annotations

from typing import cast

from langgraph.runtime import Runtime

from cognieda.application.ports import ExecutorDispatcherPort
from cognieda.execution import (
    Capability,
    ExecutionRequest,
    ExecutionStatus,
    ExecutorInput,
    normalize_for_planner,
)
from cognieda.schemas.artifacts import Assumption, Objective, Task
from cognieda.schemas.enums import TaskKind, TaskStatus

from .context import Context
from .model import PlannerDecisionModel
from .types import (
    PlannerAction,
    PlannerAnswerInput,
    PlannerControlledError,
    PlannerDecision,
    PlannerErrorCode,
    PlannerModelInput,
    State,
)


def _error(code: PlannerErrorCode, message: str) -> PlannerControlledError:
    return PlannerControlledError(code=code, message=message)


def _explicit_decision(
    query: str,
) -> tuple[PlannerDecision | None, PlannerControlledError | None] | None:
    stripped = query.strip()
    if not stripped.startswith("/"):
        return None

    command, _, payload = stripped.partition(" ")
    command = command.casefold()
    payload = payload.strip()

    if command == "/summary":
        if payload:
            return None, _error(
                PlannerErrorCode.INVALID_COMMAND,
                "The /summary command does not accept additional text.",
            )
        return PlannerDecision(action=PlannerAction.STATE_SUMMARY), None

    if command in {"/objective", "/assumption", "/answer", "/profile", "/analyze", "/transform"}:
        if not payload:
            return None, _error(
                PlannerErrorCode.INVALID_COMMAND,
                f"The {command} command requires request text.",
            )
        if command == "/objective":
            return (
                PlannerDecision(
                    action=PlannerAction.SET_OR_REFINE_OBJECTIVE,
                    objective_text=payload,
                ),
                None,
            )
        if command == "/assumption":
            return (
                PlannerDecision(
                    action=PlannerAction.ADD_ASSUMPTION,
                    assumption_text=payload,
                ),
                None,
            )
        if command == "/answer":
            return PlannerDecision(action=PlannerAction.ANSWER_FROM_STATE), None

        capability = {
            "/profile": Capability.DATA_PROFILING,
            "/analyze": Capability.DATA_ANALYSIS,
            "/transform": Capability.DATA_TRANSFORMATION,
        }[command]
        return (
            PlannerDecision(
                action=PlannerAction.CREATE_OR_RUN_DATA_TASK,
                task_instruction=payload,
                capability=capability,
            ),
            None,
        )

    return None, _error(
        PlannerErrorCode.INVALID_COMMAND,
        (
            f"Unknown Planner command {command}. Supported commands are /objective, "
            "/assumption, /profile, /analyze, /transform, /answer, and /summary."
        ),
    )


async def understand_request(state: State, runtime: Runtime[Context]) -> State:
    """Produce one typed intent from explicit syntax or the latest natural-language request."""

    explicit = _explicit_decision(state.query)
    if explicit is not None:
        state.decision, state.error = explicit
        return state

    model = cast(PlannerDecisionModel, runtime.context.planner_model)
    try:
        result = await model.decide(
            PlannerModelInput.from_planning_context(
                state.query,
                runtime.context.planning_context,
            ),
            message_history=(
                runtime.context.planning_context.conversation_history.model_messages()
            ),
        )
        state.decision = result.output
        state.new_messages = (*state.new_messages, *result.new_messages)
    except Exception as exc:
        state.error = _error(
            PlannerErrorCode.INVALID_MODEL_DECISION,
            f"Planner could not produce a valid typed decision: {exc}",
        )
    return state


async def prepare_results(state: State, runtime: Runtime[Context]) -> State:
    """Construct explicit bounded domain results without mutating input context."""

    if state.error is not None or state.decision is None:
        return state

    decision = state.decision
    planning_context = runtime.context.planning_context
    try:
        if decision.action is PlannerAction.SET_OR_REFINE_OBJECTIVE:
            assert decision.objective_text is not None
            current = planning_context.objective
            if current is None or current.text != decision.objective_text:
                state.created_objective = Objective(text=decision.objective_text)
        elif decision.action is PlannerAction.ADD_ASSUMPTION:
            assert decision.assumption_text is not None
            state.created_assumption = Assumption(text=decision.assumption_text)
        elif decision.action is PlannerAction.CREATE_OR_RUN_DATA_TASK:
            assert decision.task_instruction is not None
            assert decision.capability is not None
            objective = planning_context.objective
            if objective is None:
                if decision.objective_text is None:
                    state.error = _error(
                        PlannerErrorCode.MISSING_OBJECTIVE,
                        "Data work requires a clear active Objective before a Task can run.",
                    )
                    return state
                objective = Objective(text=decision.objective_text)
                state.created_objective = objective
            state.created_task = Task(
                objective_id=objective.objective_id,
                kind=TaskKind.DATA,
                instruction=decision.task_instruction,
                status=TaskStatus.PENDING,
            )
            state.selected_capability = decision.capability
        elif decision.action is PlannerAction.INVALID_OR_UNSUPPORTED:
            state.error = _error(
                PlannerErrorCode.UNSUPPORTED_ACTION,
                decision.message or "The requested action is unsupported by the MVP Planner.",
            )
    except (TypeError, ValueError) as exc:
        state.error = _error(
            PlannerErrorCode.INVALID_SUCCESSOR_STATE,
            f"Planner rejected an invalid typed result: {exc}",
        )
    return state


def _with_task_status(task: Task, status: TaskStatus) -> Task:
    return Task(
        task_id=task.task_id,
        objective_id=task.objective_id,
        kind=task.kind,
        instruction=task.instruction,
        status=status,
    )


async def dispatch_work(state: State, runtime: Runtime[Context]) -> State:
    """Run only a tracked Task and consume its bounded PlannerWorkOutcome projection."""

    if (
        state.error is not None
        or state.created_task is None
        or state.selected_capability is None
    ):
        return state

    dispatcher = cast(ExecutorDispatcherPort, runtime.context.dispatcher)
    task = state.created_task
    task_id = task.task_id
    try:
        running_task = _with_task_status(task, TaskStatus.RUNNING)
        state.created_task = running_task
        result = await dispatcher.dispatch(
            ExecutionRequest(
                capability=state.selected_capability,
                input=ExecutorInput(task=running_task),
                context=state.execution_context,
            )
        )
        outcome = normalize_for_planner(result)
        state.work_outcome = outcome
        if outcome.task_id != task_id:
            state.created_task = _with_task_status(running_task, TaskStatus.FAILED)
            state.error = _error(
                PlannerErrorCode.TASK_OUTCOME_MISMATCH,
                "Executor outcome Task identity did not match the dispatched Task.",
            )
            return state

        terminal_status = (
            TaskStatus.COMPLETED
            if outcome.status is ExecutionStatus.SUCCEEDED
            else TaskStatus.FAILED
        )
        state.created_task = _with_task_status(running_task, terminal_status)
    except Exception as exc:
        state.created_task = _with_task_status(task, TaskStatus.FAILED)
        state.error = _error(
            PlannerErrorCode.DISPATCH_FAILED,
            f"Planner could not complete dispatcher work: {exc}",
        )
    return state


def _outcome_details(state: State) -> str:
    if (
        state.error is not None
        and state.error.code is PlannerErrorCode.TASK_OUTCOME_MISMATCH
    ):
        return ""
    outcome = state.work_outcome
    if outcome is None:
        return ""
    details = [*outcome.blockers, *outcome.limitations]
    if outcome.permitted_next_actions:
        details.append(
            "Permitted next actions: " + ", ".join(outcome.permitted_next_actions) + "."
        )
    return " " + " ".join(details) if details else ""


async def compose_response(state: State, runtime: Runtime[Context]) -> State:
    """Compose a human-facing response without upgrading non-admitted work to Evidence."""

    if state.error is not None:
        state.response = state.error.message + _outcome_details(state)
        return state

    decision = state.decision
    if decision is None:
        state.error = _error(
            PlannerErrorCode.MODEL_UNAVAILABLE,
            "Planner request understanding is unavailable.",
        )
        state.response = state.error.message
        return state

    if decision.action is PlannerAction.ANSWER_FROM_STATE:
        planning_context = runtime.context.planning_context
        if not planning_context.evidences:
            state.error = _error(
                PlannerErrorCode.NO_ADMITTED_EVIDENCE,
                "No admitted Evidence is available to support an empirical answer.",
            )
            state.response = state.error.message
            return state
        model = cast(PlannerDecisionModel, runtime.context.planner_model)
        try:
            result = await model.answer(
                PlannerAnswerInput(
                    latest_request=state.query,
                    objective=planning_context.objective,
                    data_profile=planning_context.data_profile,
                    evidences=planning_context.evidences,
                )
            )
            state.response = result.output.text
            state.new_messages = (*state.new_messages, *result.new_messages)
        except Exception as exc:
            state.error = _error(
                PlannerErrorCode.RESPONSE_FAILED,
                f"Planner could not compose a typed Evidence-grounded response: {exc}",
            )
            state.response = state.error.message
        return state

    if decision.action is PlannerAction.STATE_SUMMARY:
        planning_context = runtime.context.planning_context
        objective_text = (
            planning_context.objective.text
            if planning_context.objective is not None
            else "not established"
        )
        state.response = (
            f"Active Objective: {objective_text}. "
            f"Planning Assumptions (not Evidence): {len(planning_context.assumptions)}. "
            f"Tasks: {len(planning_context.tasks)}. "
            f"Admitted Evidence items: {len(planning_context.evidences)}."
        )
    elif decision.action is PlannerAction.SET_OR_REFINE_OBJECTIVE:
        active_objective = state.created_objective or runtime.context.planning_context.objective
        assert active_objective is not None
        state.response = f"Active Objective set to: {active_objective.text}"
    elif decision.action is PlannerAction.ADD_ASSUMPTION:
        assert decision.assumption_text is not None
        state.response = (
            f"Planning Assumption recorded: {decision.assumption_text} "
            "It is not empirical Evidence."
        )
    elif decision.action is PlannerAction.CREATE_OR_RUN_DATA_TASK:
        outcome = state.work_outcome
        if outcome is None:
            state.response = "The bounded Task was created but no executor outcome was returned."
        elif outcome.status is ExecutionStatus.SUCCEEDED:
            state.response = (
                "The requested work completed at the executor boundary. No Evidence was "
                "admitted, so the outcome is not an authoritative empirical finding."
                + _outcome_details(state)
            )
        else:
            state.response = (
                f"The requested work ended with executor status {outcome.status.value}. "
                "No Evidence was created."
                + _outcome_details(state)
            )
    else:
        state.response = decision.message or "The requested action is unsupported."
    return state
