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
from cognieda.schemas.enums import TaskStatus

from .model import PlannerDecisionModel
from .types import (
    Context,
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
        state.decision = await model.decide(
            PlannerModelInput.from_frame(
                state.query,
                state.session_frame,
                conversation=state.conversation_context,
            )
        )
    except Exception as exc:
        state.error = _error(
            PlannerErrorCode.INVALID_MODEL_DECISION,
            f"Planner could not produce a valid typed decision: {exc}",
        )
    return state


async def apply_planning_state(state: State, runtime: Runtime[Context]) -> State:
    """Apply validated Objective, Assumption, or Task proposals through SessionFrame seams."""

    del runtime
    if state.error is not None or state.decision is None:
        return state

    decision = state.decision
    try:
        if decision.action is PlannerAction.SET_OR_REFINE_OBJECTIVE:
            assert decision.objective_text is not None
            current = state.session_frame.objective
            if current is None or current.text != decision.objective_text:
                state.session_frame = state.session_frame.set_objective(
                    Objective(text=decision.objective_text)
                )
        elif decision.action is PlannerAction.ADD_ASSUMPTION:
            assert decision.assumption_text is not None
            state.session_frame = state.session_frame.add_assumption(
                Assumption(text=decision.assumption_text)
            )
        elif decision.action is PlannerAction.CREATE_OR_RUN_DATA_TASK:
            assert decision.task_instruction is not None
            assert decision.capability is not None
            if state.session_frame.objective is None:
                if decision.objective_text is None:
                    state.error = _error(
                        PlannerErrorCode.MISSING_OBJECTIVE,
                        "Data work requires a clear active Objective before a Task can run.",
                    )
                    return state
                state.session_frame = state.session_frame.set_objective(
                    Objective(text=decision.objective_text)
                )
            task = Task(instruction=decision.task_instruction, status=TaskStatus.PENDING)
            state.session_frame = state.session_frame.add_task(task)
            state.created_task_id = task.task_id
            state.selected_capability = decision.capability
        elif decision.action is PlannerAction.INVALID_OR_UNSUPPORTED:
            state.error = _error(
                PlannerErrorCode.UNSUPPORTED_ACTION,
                decision.message or "The requested action is unsupported by the MVP Planner.",
            )
    except (TypeError, ValueError) as exc:
        state.error = _error(
            PlannerErrorCode.INVALID_SUCCESSOR_STATE,
            f"Planner rejected an invalid successor SessionFrame: {exc}",
        )
    return state


def _task_by_id(state: State, task_id: object) -> Task:
    for task in state.session_frame.tasks:
        if task.task_id == task_id:
            return task
    raise ValueError("Task is missing from the active SessionFrame.")


async def dispatch_work(state: State, runtime: Runtime[Context]) -> State:
    """Run only a tracked Task and consume its bounded PlannerWorkOutcome projection."""

    if (
        state.error is not None
        or state.created_task_id is None
        or state.selected_capability is None
    ):
        return state

    dispatcher = cast(ExecutorDispatcherPort, runtime.context.dispatcher)
    task_id = state.created_task_id
    try:
        state.session_frame = state.session_frame.set_task_status(task_id, TaskStatus.RUNNING)
        running_task = _task_by_id(state, task_id)
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
            state.session_frame = state.session_frame.set_task_status(task_id, TaskStatus.FAILED)
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
        state.session_frame = state.session_frame.set_task_status(task_id, terminal_status)
    except Exception as exc:
        try:
            state.session_frame = state.session_frame.set_task_status(task_id, TaskStatus.FAILED)
        except ValueError:
            pass
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
        if not state.session_frame.evidences:
            state.error = _error(
                PlannerErrorCode.NO_ADMITTED_EVIDENCE,
                "No admitted Evidence is available to support an empirical answer.",
            )
            state.response = state.error.message
            return state
        model = cast(PlannerDecisionModel, runtime.context.planner_model)
        try:
            draft = await model.answer(
                PlannerAnswerInput(
                    latest_request=state.query,
                    objective=state.session_frame.objective,
                    data_profile=state.session_frame.data_profile,
                    evidences=state.session_frame.evidences,
                )
            )
            state.response = draft.text
        except Exception as exc:
            state.error = _error(
                PlannerErrorCode.RESPONSE_FAILED,
                f"Planner could not compose a typed Evidence-grounded response: {exc}",
            )
            state.response = state.error.message
        return state

    if decision.action is PlannerAction.STATE_SUMMARY:
        objective = (
            state.session_frame.objective.text
            if state.session_frame.objective is not None
            else "not established"
        )
        state.response = (
            f"Active Objective: {objective}. "
            f"Planning Assumptions (not Evidence): {len(state.session_frame.assumptions)}. "
            f"Tasks: {len(state.session_frame.tasks)}. "
            f"Admitted Evidence items: {len(state.session_frame.evidences)}."
        )
    elif decision.action is PlannerAction.SET_OR_REFINE_OBJECTIVE:
        assert state.session_frame.objective is not None
        state.response = f"Active Objective set to: {state.session_frame.objective.text}"
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
