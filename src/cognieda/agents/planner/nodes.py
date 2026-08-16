from __future__ import annotations

from collections.abc import Awaitable, Callable

from langgraph.graph import END
from langgraph.runtime import Runtime
from langgraph.types import Command, interrupt

from cognieda.schemas.plan import Plan

from .context import PlannerContext, PlannerRunContext
from .dependencies import PlanAdmissionPort
from .state import PlannerState, PlannerTurnOutcome
from .types import PlannerControlledError, PlannerErrorCode, PlannerOutput


async def plan_or_answer(
    state: PlannerState,
    runtime: Runtime[PlannerRunContext],
    *,
    invoke_cognitive: Callable[..., Awaitable[PlannerOutput]],
) -> Command[str]:
    run_context: PlannerRunContext = runtime.context
    planner_context: PlannerContext = run_context.planner_context
    message_history = list(run_context.message_history)

    current_completed_segments = tuple(state.get("completed_segments") or ())

    request = state.get("latest_human_input")
    if request is None or not request.strip():
        error = PlannerControlledError(
            code=PlannerErrorCode.INVALID_LIFECYCLE_STATE,
            message="Planner lifecycle requires a non-empty Human request.",
        )
        return Command(
            update={
                "turn_outcome": PlannerTurnOutcome(error=error),
                "completed_segments": current_completed_segments,
            },
            goto=END,
        )

    candidate_plan = state.get("candidate_plan")

    output = await invoke_cognitive(
        request,
        context=planner_context,
        candidate_plan=candidate_plan,
        message_history=message_history,
    )
    result = output.result
    base_update: dict[str, object] = {
        "candidate_plan": candidate_plan,
        "completed_segments": current_completed_segments,
    }

    if output.error is not None:
        outcome = PlannerTurnOutcome(response=result.response, error=output.error)
        return Command(update={**base_update, "turn_outcome": outcome}, goto=END)

    try:
        if result.discard_candidate and candidate_plan is None:
            raise ValueError("discard_candidate requires a retained candidate.")
        if (
            result.continue_execution
            and candidate_plan is None
            and len(planner_context.active_plans) != 1
        ):
            raise ValueError(
                "continue_execution without candidate requires exactly one active Plan."
            )
    except ValueError:
        error = PlannerControlledError(
            code=PlannerErrorCode.INVALID_LIFECYCLE_STATE,
            message="Planner produced a result that is invalid for the retained lifecycle state.",
        )
        return Command(
            update={**base_update, "turn_outcome": PlannerTurnOutcome(error=error)},
            goto=END,
        )

    segment = output.segment
    completed_segments = (
        (*current_completed_segments, segment)
        if segment is not None
        else current_completed_segments
    )

    if result.plan is not None:
        outcome = PlannerTurnOutcome(
            proposed_plan=result.plan,
            response=result.response,
            human_input_request=result.human_input_request,
        )
        return Command(
            update={
                "candidate_plan": result.plan,
                "completed_segments": completed_segments,
                "turn_outcome": outcome,
            },
            goto="await_human",
        )

    if result.continue_execution:
        if candidate_plan is not None:
            return Command(
                update={
                    "candidate_plan": candidate_plan,
                    "completed_segments": completed_segments,
                },
                goto="admit_candidate",
            )
        outcome = PlannerTurnOutcome(
            response=(
                "The active Plan is ready to continue, but Plan execution is not "
                "implemented in this runtime phase."
            )
        )
        return Command(
            update={
                "candidate_plan": None,
                "completed_segments": completed_segments,
                "turn_outcome": outcome,
            },
            goto=END,
        )

    if result.discard_candidate:
        outcome = PlannerTurnOutcome(
            response=result.response or "The proposed Plan was discarded."
        )
        return Command(
            update={
                "candidate_plan": None,
                "completed_segments": completed_segments,
                "turn_outcome": outcome,
            },
            goto=END,
        )

    outcome = PlannerTurnOutcome(
        response=result.response,
        human_input_request=result.human_input_request,
    )
    awaiting_human = (
        result.human_input_request is not None or candidate_plan is not None
    )
    return Command(
        update={
            "candidate_plan": candidate_plan,
            "completed_segments": completed_segments,
            "turn_outcome": outcome,
        },
        goto="await_human" if awaiting_human else END,
    )


def await_human(
    state: PlannerState,
) -> dict[str, object]:
    outcome = state.get("turn_outcome")
    if outcome is None:
        raise ValueError("Human wait requires a typed Planner turn outcome.")

    if outcome.human_input_request is not None:
        reason = "human_clarification"
    elif outcome.proposed_plan is not None:
        reason = "candidate_review"
    else:
        reason = "candidate_followup"
    answer: str = interrupt({"reason": reason})
    return {
        "latest_human_input": answer,
        "turn_outcome": None,
        "completed_segments": (),
    }


def admit_candidate(
    state: PlannerState,
    *,
    plan_admission: PlanAdmissionPort,
) -> dict[str, object]:
    plan: Plan | None = state.get("candidate_plan")
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
