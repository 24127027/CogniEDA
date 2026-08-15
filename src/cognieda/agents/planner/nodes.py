from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Literal

from langgraph.types import Command, interrupt
from pydantic_ai.messages import ModelMessage

from cognieda.schemas.plan import Plan

from .context import PlannerContext
from .dependencies import PlanAdmissionPort, PlannerContextProviderPort
from .state import PlannerState, PlannerTurnOutcome
from .types import PlannerControlledError, PlannerErrorCode, PlannerOutput

_ACTIVE_PLAN_EXECUTION_DEFERRED = (
    "The active Plan is ready to continue, but Plan execution is not implemented "
    "in this runtime phase."
)
_CANDIDATE_ADMITTED = "The proposed Plan was admitted and activated."
_CANDIDATE_DISCARDED = "The proposed Plan was discarded."
_END_NODE: Literal["__end__"] = "__end__"
_InvokeCognitive = Callable[..., Awaitable[PlannerOutput]]


async def plan_or_answer(
    state: PlannerState,
    *,
    invoke_cognitive: _InvokeCognitive,
    planner_context_provider: PlannerContextProviderPort,
) -> Command[Literal["await_human", "admit_candidate", "__end__"]]:
    request = state["latest_human_input"]
    if request is None or not request.strip():
        error = PlannerControlledError(
            code=PlannerErrorCode.INVALID_LIFECYCLE_STATE,
            message="Planner lifecycle requires a non-empty Human request.",
        )
        return Command(
            update={"turn_outcome": PlannerTurnOutcome(error=error)},
            goto=_END_NODE,
        )

    try:
        planner_context: PlannerContext = planner_context_provider.materialize()
    except Exception:
        error = PlannerControlledError(
            code=PlannerErrorCode.INVALID_LIFECYCLE_STATE,
            message="Planner authoritative context could not be materialized.",
        )
        return Command(
            update={"turn_outcome": PlannerTurnOutcome(error=error)},
            goto=_END_NODE,
        )

    output = await invoke_cognitive(
        request,
        context=planner_context,
        candidate_plan=state["candidate_plan"],
        message_history=list(state["messages"]),
    )
    messages: tuple[ModelMessage, ...] = (*state["messages"], *output.messages)
    result = output.result
    base_update: dict[str, object] = {"messages": messages}

    if output.error is not None:
        outcome = PlannerTurnOutcome(response=result.response, error=output.error)
        return Command(update={**base_update, "turn_outcome": outcome}, goto=_END_NODE)

    try:
        if result.discard_candidate and state["candidate_plan"] is None:
            raise ValueError("discard_candidate requires a retained candidate.")
        if (
            result.continue_execution
            and state["candidate_plan"] is None
            and planner_context.active_plan is None
        ):
            raise ValueError("continue_execution requires a retained or active Plan.")
    except ValueError:
        error = PlannerControlledError(
            code=PlannerErrorCode.INVALID_LIFECYCLE_STATE,
            message="Planner produced a result that is invalid for the retained lifecycle state.",
        )
        return Command(
            update={**base_update, "turn_outcome": PlannerTurnOutcome(error=error)},
            goto=_END_NODE,
        )

    if result.plan is not None:
        outcome = PlannerTurnOutcome(
            proposed_plan=result.plan,
            response=result.response,
            human_input_request=result.human_input_request,
        )
        return Command(
            update={
                **base_update,
                "candidate_plan": result.plan,
                "turn_outcome": outcome,
            },
            goto="await_human",
        )

    if result.continue_execution:
        if state["candidate_plan"] is not None:
            return Command(update=base_update, goto="admit_candidate")
        outcome = PlannerTurnOutcome(response=_ACTIVE_PLAN_EXECUTION_DEFERRED)
        return Command(update={**base_update, "turn_outcome": outcome}, goto=_END_NODE)

    if result.discard_candidate:
        outcome = PlannerTurnOutcome(response=result.response or _CANDIDATE_DISCARDED)
        return Command(
            update={
                **base_update,
                "candidate_plan": None,
                "turn_outcome": outcome,
            },
            goto=_END_NODE,
        )

    outcome = PlannerTurnOutcome(
        response=result.response,
        human_input_request=result.human_input_request,
    )
    awaiting_human = (
        result.human_input_request is not None or state["candidate_plan"] is not None
    )
    return Command(
        update={**base_update, "turn_outcome": outcome},
        goto="await_human" if awaiting_human else _END_NODE,
    )


def await_human(
    state: PlannerState,
) -> Command[Literal["plan_or_answer", "__end__"]]:
    outcome = state["turn_outcome"]
    if outcome is None:
        raise ValueError("Human wait requires a typed Planner turn outcome.")

    if outcome.human_input_request is not None:
        reason = "human_clarification"
    elif outcome.proposed_plan is not None:
        reason = "candidate_review"
    else:
        reason = "candidate_followup"
    answer = interrupt({"reason": reason})
    if not isinstance(answer, str) or not answer.strip():
        error = PlannerControlledError(
            code=PlannerErrorCode.INVALID_REQUEST,
            message="Planner requests cannot be empty.",
        )
        return Command(
            update={
                "latest_human_input": None,
                "turn_outcome": PlannerTurnOutcome(error=error),
            },
            goto=_END_NODE,
        )
    return Command(
        update={"latest_human_input": answer, "turn_outcome": None},
        goto="plan_or_answer",
    )


def admit_candidate(
    state: PlannerState,
    *,
    plan_admission: PlanAdmissionPort,
) -> dict[str, object]:
    plan: Plan | None = state["candidate_plan"]
    if plan is None:
        raise ValueError("Candidate admission requires a retained candidate Plan.")
    try:
        plan_admission.admit(plan)
    except Exception:
        error = PlannerControlledError(
            code=PlannerErrorCode.PLAN_ADMISSION_FAILED,
            message="The proposed Plan could not be admitted; the candidate remains available.",
        )
        return {"turn_outcome": PlannerTurnOutcome(error=error)}
    return {
        "candidate_plan": None,
        "turn_outcome": PlannerTurnOutcome(response=_CANDIDATE_ADMITTED),
    }


__all__ = ("admit_candidate", "await_human", "plan_or_answer")
