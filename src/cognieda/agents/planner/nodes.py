from __future__ import annotations

from typing import Literal

from langgraph.runtime import Runtime
from langgraph.types import Command, interrupt

from .dependencies import PlannerGraphContext
from .state import PlannerState, PlannerTurnOutcome
from .types import PlannerControlledError, PlannerErrorCode

_ACTIVE_PLAN_EXECUTION_DEFERRED = (
    "The active Plan is ready to continue, but Plan execution is not implemented "
    "in this runtime phase."
)
_CANDIDATE_ADMITTED = "The proposed Plan was admitted and activated."
_CANDIDATE_DISCARDED = "The proposed Plan was discarded."
_END_NODE: Literal["__end__"] = "__end__"


def validate_candidate_state(state: PlannerState) -> None:
    plan = state["candidate_plan"]
    tasks = state["candidate_tasks"]
    if plan is None:
        if tasks:
            raise ValueError("Candidate Tasks require a retained candidate Plan.")
        return
    plan.validate_tasks(tasks)


def controlled_error(
    code: PlannerErrorCode,
    message: str,
) -> PlannerControlledError:
    return PlannerControlledError(code=code, message=message)


async def plan_or_answer(
    state: PlannerState,
    runtime: Runtime[PlannerGraphContext],
) -> Command[Literal["await_human", "admit_candidate", "__end__"]]:
    validate_candidate_state(state)
    request = state["latest_human_input"]
    if request is None or not request.strip():
        error = controlled_error(
            PlannerErrorCode.INVALID_LIFECYCLE_STATE,
            "Planner lifecycle requires a non-empty Human request.",
        )
        return Command(
            update={
                "result": None,
                "error": error,
                "turn_outcome": PlannerTurnOutcome(error=error),
            },
            goto=_END_NODE,
        )

    try:
        planner_context = runtime.context.planner_context_provider.materialize()
    except Exception:
        error = controlled_error(
            PlannerErrorCode.INVALID_LIFECYCLE_STATE,
            "Planner authoritative context could not be materialized.",
        )
        return Command(
            update={
                "result": None,
                "error": error,
                "turn_outcome": PlannerTurnOutcome(error=error),
            },
            goto=_END_NODE,
        )

    output = await runtime.context.invoke_cognitive(
        request,
        context=planner_context,
        candidate_plan=state["candidate_plan"],
        candidate_tasks=state["candidate_tasks"],
        message_history=list(state["messages"]),
    )
    messages = (*state["messages"], *output.messages)
    result = output.result
    base_update: dict[str, object] = {
        "messages": messages,
        "result": result,
        "error": output.error,
    }

    if output.error is not None:
        outcome = PlannerTurnOutcome(response=result.response, error=output.error)
        return Command(update={**base_update, "turn_outcome": outcome}, goto=_END_NODE)

    try:
        if result.plan is not None:
            result.plan.validate_tasks(result.tasks)
        if result.discard_candidate and state["candidate_plan"] is None:
            raise ValueError("discard_candidate requires a retained candidate.")
        if (
            result.continue_execution
            and state["candidate_plan"] is None
            and planner_context.active_plan is None
        ):
            raise ValueError("continue_execution requires a retained or active Plan.")
    except ValueError:
        error = controlled_error(
            PlannerErrorCode.INVALID_LIFECYCLE_STATE,
            "Planner produced a result that is invalid for the retained lifecycle state.",
        )
        return Command(
            update={
                **base_update,
                "error": error,
                "turn_outcome": PlannerTurnOutcome(error=error),
            },
            goto=_END_NODE,
        )

    if result.plan is not None:
        outcome = PlannerTurnOutcome(
            candidate_plan=result.plan,
            candidate_tasks=result.tasks,
            response=result.response,
            human_input_request=result.human_input_request,
            awaiting_human=True,
        )
        return Command(
            update={
                **base_update,
                "candidate_plan": result.plan,
                "candidate_tasks": result.tasks,
                "turn_outcome": outcome,
            },
            goto="await_human",
        )

    if result.continue_execution:
        if state["candidate_plan"] is not None:
            return Command(update=base_update, goto="admit_candidate")
        outcome = PlannerTurnOutcome(
            response=_ACTIVE_PLAN_EXECUTION_DEFERRED,
            active_plan_continuation_deferred=True,
        )
        return Command(update={**base_update, "turn_outcome": outcome}, goto=_END_NODE)

    if result.discard_candidate:
        outcome = PlannerTurnOutcome(
            response=result.response or _CANDIDATE_DISCARDED,
            candidate_discarded=True,
        )
        return Command(
            update={
                **base_update,
                "candidate_plan": None,
                "candidate_tasks": (),
                "turn_outcome": outcome,
            },
            goto=_END_NODE,
        )

    awaiting_human = (
        result.human_input_request is not None or state["candidate_plan"] is not None
    )
    outcome = PlannerTurnOutcome(
        response=result.response,
        human_input_request=result.human_input_request,
        awaiting_human=awaiting_human,
    )
    return Command(
        update={**base_update, "turn_outcome": outcome},
        goto="await_human" if awaiting_human else _END_NODE,
    )


def interrupt_reason(outcome: PlannerTurnOutcome) -> str:
    if outcome.human_input_request is not None:
        return "human_clarification"
    if outcome.candidate_plan is not None:
        return "candidate_review"
    return "candidate_followup"


def await_human(
    state: PlannerState,
) -> Command[Literal["plan_or_answer", "__end__"]]:
    outcome = state["turn_outcome"]
    if outcome is None:
        raise ValueError("Human wait requires a typed Planner turn outcome.")

    answer = interrupt({"reason": interrupt_reason(outcome)})
    if not isinstance(answer, str) or not answer.strip():
        error = controlled_error(
            PlannerErrorCode.INVALID_REQUEST,
            "Planner requests cannot be empty.",
        )
        return Command(
            update={
                "latest_human_input": None,
                "result": None,
                "error": error,
                "turn_outcome": PlannerTurnOutcome(error=error),
            },
            goto=_END_NODE,
        )
    return Command(
        update={
            "latest_human_input": answer,
            "result": None,
            "error": None,
            "turn_outcome": None,
        },
        goto="plan_or_answer",
    )


def admit_candidate(
    state: PlannerState,
    runtime: Runtime[PlannerGraphContext],
) -> dict[str, object]:
    validate_candidate_state(state)
    plan = state["candidate_plan"]
    if plan is None:
        raise ValueError("Candidate admission requires a retained candidate Plan.")
    try:
        runtime.context.plan_admission.admit(
            plan,
            tasks=state["candidate_tasks"],
        )
    except Exception:
        error = controlled_error(
            PlannerErrorCode.PLAN_ADMISSION_FAILED,
            "The proposed Plan could not be admitted; the candidate remains available.",
        )
        return {
            "error": error,
            "turn_outcome": PlannerTurnOutcome(error=error),
        }
    return {
        "candidate_plan": None,
        "candidate_tasks": (),
        "error": None,
        "turn_outcome": PlannerTurnOutcome(
            response=_CANDIDATE_ADMITTED,
            candidate_admitted=True,
        ),
    }


__all__ = (
    "admit_candidate",
    "await_human",
    "controlled_error",
    "interrupt_reason",
    "plan_or_answer",
    "validate_candidate_state",
)
