from __future__ import annotations

from collections.abc import Awaitable, Callable

from langgraph.graph import END
from langgraph.types import Command, interrupt
from pydantic_ai.messages import ModelMessage

from cognieda.schemas.plan import Plan

from .context import PlannerContext
from .dependencies import PlanAdmissionPort, PlannerContextProviderPort
from .state import PlannerState, PlannerTurnOutcome
from .types import PlannerControlledError, PlannerErrorCode, PlannerOutput


async def plan_or_answer(
    state: PlannerState,
    *,
    invoke_cognitive: Callable[..., Awaitable[PlannerOutput]],
    planner_context_provider: PlannerContextProviderPort,
) -> Command[str]:
    request = state["latest_human_input"]
    if request is None or not request.strip():
        error = PlannerControlledError(
            code=PlannerErrorCode.INVALID_LIFECYCLE_STATE,
            message="Planner lifecycle requires a non-empty Human request.",
        )
        return Command(
            update={"turn_outcome": PlannerTurnOutcome(error=error)},
            goto=END,
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
            goto=END,
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
        return Command(update={**base_update, "turn_outcome": outcome}, goto=END)

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
            goto=END,
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
        outcome = PlannerTurnOutcome(
            response=(
                "The active Plan is ready to continue, but Plan execution is not "
                "implemented in this runtime phase."
            )
        )
        return Command(update={**base_update, "turn_outcome": outcome}, goto=END)

    if result.discard_candidate:
        outcome = PlannerTurnOutcome(
            response=result.response or "The proposed Plan was discarded."
        )
        return Command(
            update={
                **base_update,
                "candidate_plan": None,
                "turn_outcome": outcome,
            },
            goto=END,
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
        goto="await_human" if awaiting_human else END,
    )


def await_human(
    state: PlannerState,
) -> dict[str, object]:
    outcome = state["turn_outcome"]
    if outcome is None:
        raise ValueError("Human wait requires a typed Planner turn outcome.")

    if outcome.human_input_request is not None:
        reason = "human_clarification"
    elif outcome.proposed_plan is not None:
        reason = "candidate_review"
    else:
        reason = "candidate_followup"
    answer: str = interrupt({"reason": reason})
    return {"latest_human_input": answer, "turn_outcome": None}


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
        "turn_outcome": PlannerTurnOutcome(
            response="The proposed Plan was admitted and activated."
        ),
    }


__all__ = ("admit_candidate", "await_human", "plan_or_answer")
