from __future__ import annotations

from .contracts import PlannerCognitiveResult, PlannerControlledError, PlannerErrorCode
from .state import PlannerState


def fail_state(
    state: PlannerState,
    code: PlannerErrorCode,
    message: str,
) -> PlannerState:
    """Return one controlled Human-facing failure without arbitrary exception detail."""

    state.error = PlannerControlledError(code=code, message=message)
    state.cognitive_result = PlannerCognitiveResult(response=message)
    return state


def plan_prompt(state: PlannerState) -> str:
    feedback = (
        f"\n\nExplicit Human or execution feedback:\n{state.human_feedback}"
        if state.human_feedback is not None
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
    approved: PlannerCognitiveResult,
) -> str:
    return (
        "Execute only this exact Human-approved Plan bundle:\n"
        f"{approved.model_dump_json()}\n\n"
        "Readable Planner context (only admitted Evidence and governed Discovery may "
        "support empirical claims):\n"
        f"{state.context.model_dump_json()}"
    )


__all__ = ("execute_prompt", "fail_state", "plan_prompt")
