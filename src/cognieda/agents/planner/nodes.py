from __future__ import annotations

from cognieda.schemas.plan import Plan

from .contracts import PlannerControlledError, PlannerErrorCode, PlannerResult
from .state import PlannerState


def fail_state(
    state: PlannerState,
    code: PlannerErrorCode,
    message: str,
) -> PlannerState:
    """Return one controlled Human-facing failure without arbitrary exception detail."""

    state.error = PlannerControlledError(code=code, message=message)
    state.result = PlannerResult(response=message)
    return state


def block_execution(
    state: PlannerState,
    code: PlannerErrorCode,
    message: str,
) -> PlannerState:
    """Return execute control to reasoning without fabricating a PlannerResult."""

    state.result = None
    state.execution_blocker = message
    state.error = PlannerControlledError(code=code, message=message)
    return state


def plan_or_answer_prompt(state: PlannerState) -> str:
    feedback_items = tuple(
        item
        for item in (state.human_feedback, state.execution_blocker)
        if item is not None
    )
    feedback = (
        "\n\nExplicit Human or execution feedback:\n" + "\n".join(feedback_items)
        if feedback_items
        else ""
    )
    return (
        f"Current Human request:\n{state.request}\n\n"
        "Readable Planner context (ConversationHistory is non-authoritative):\n"
        f"{state.context.model_dump_json()}"
        f"{feedback}"
    )


def execute_prompt(
    state: PlannerState,
    active_plan: Plan,
) -> str:
    return (
        "Execute only the active Human-approved Plan:\n"
        f"{active_plan.model_dump_json()}\n\n"
        "Readable Planner context (only admitted Evidence and governed Discovery may "
        "support empirical claims):\n"
        f"{state.context.model_dump_json()}"
    )


__all__ = ("block_execution", "execute_prompt", "fail_state", "plan_or_answer_prompt")
