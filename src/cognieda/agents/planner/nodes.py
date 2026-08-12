from __future__ import annotations

import re
from typing import cast

from langgraph.runtime import Runtime

from cognieda.execution import Capability
from cognieda.schemas.artifacts import Assumption, Objective, Task
from cognieda.schemas.enums import TaskKind
from cognieda.schemas.plan_revision import PlanRevision, PlanTaskBinding

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
            return None
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


def _is_exact_human_assumption_source(query: str, assumption_text: str) -> bool:
    stripped = query.strip()
    command, separator, payload = stripped.partition(" ")
    if command.casefold() == "/assumption":
        return bool(separator) and payload.strip() == assumption_text

    if assumption_text not in query:
        return False
    request = query.casefold()
    return bool(
        re.search(r"\bi\s+assume\b", request)
        or re.search(
            r"\b(?:add|keep|record|retain|treat)\b.*\bassumption\b",
            request,
        )
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
        decision = result.output
        if decision.assumption_text is not None and not _is_exact_human_assumption_source(
            state.query,
            decision.assumption_text,
        ):
            state.error = _error(
                PlannerErrorCode.INVALID_MODEL_DECISION,
                "Planner cannot author or rewrite an Assumption; exact Human-supplied "
                "assumption text is required.",
            )
            return state
        state.decision = decision
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
            task = Task(
                objective_id=objective.objective_id,
                kind=TaskKind.DATA,
                instruction=decision.task_instruction,
            )
            revision = PlanRevision.create(
                objective_id=objective.objective_id,
                task_bindings=(
                    PlanTaskBinding(
                        task_id=task.task_id,
                        required_capability=decision.capability,
                        order_rank=0,
                    ),
                ),
                authoritative_tasks=(task,),
            )
            state.proposed_objective = objective
            state.proposed_tasks = (task,)
            state.proposed_plan_revision = revision
        elif decision.action is PlannerAction.INVALID_OR_UNSUPPORTED:
            if decision.assumption_is_reasonably_testable is True:
                message = (
                    "The Human-supplied claim is reasonably testable and therefore was not "
                    "retained as an Assumption. It belongs to scientific investigation, which "
                    "is not executable in the current DATA-only runtime."
                )
            else:
                message = decision.message or (
                    "The requested action is unsupported by the MVP Planner."
                )
            state.error = _error(
                PlannerErrorCode.UNSUPPORTED_ACTION,
                message,
            )
    except (TypeError, ValueError) as exc:
        state.error = _error(
            PlannerErrorCode.INVALID_SUCCESSOR_STATE,
            f"Planner rejected an invalid typed result: {exc}",
        )
    return state


async def compose_response(state: State, runtime: Runtime[Context]) -> State:
    """Compose a human-facing response without upgrading non-admitted work to Evidence."""

    if state.error is not None:
        state.response = state.error.message
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
            "The Human supplied this statement, and Planner classified it as not reasonably "
            "testable. It is planning context, not empirical Evidence."
        )
    elif decision.action is PlannerAction.CREATE_OR_RUN_DATA_TASK:
        objective = state.proposed_objective
        revision = state.proposed_plan_revision
        assert objective is not None
        assert revision is not None
        state.response = (
            f"Proposed transient PlanRevision {revision.plan_revision_id} for Objective: "
            f"{objective.text} with {len(state.proposed_tasks)} DATA Task. No authoritative "
            "state or execution exists yet. Use /approve to commit this pending plan or "
            "/reject to discard it."
        )
    else:
        state.response = decision.message or "The requested action is unsupported."
    return state
