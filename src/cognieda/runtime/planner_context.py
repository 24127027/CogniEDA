from __future__ import annotations

from cognieda.agents.planner.context import PlannerContext
from cognieda.runtime.conversation import ConversationHistory
from cognieda.schemas.artifacts import SessionFrame, Task
from cognieda.schemas.plan import Plan


def build_planner_context(
    session_frame: SessionFrame,
    conversation_history: ConversationHistory,
    *,
    pending_plan: Plan | None = None,
    pending_tasks: tuple[Task, ...] = (),
    active_plan: Plan | None = None,
) -> PlannerContext:
    """Materialize retained readable state without filtering or authority changes."""

    if active_plan is not None and active_plan.objective != session_frame.objective:
        raise ValueError("Active Plan must match the exact SessionFrame Objective.")
    return PlannerContext(
        pending_plan=pending_plan,
        pending_tasks=pending_tasks,
        active_plan=active_plan,
        objective=session_frame.objective,
        assumptions=session_frame.assumptions,
        tasks=session_frame.tasks,
        evidences=session_frame.evidences,
        discoveries=session_frame.discoveries,
        data_profile=session_frame.data_profile,
        conversation_history=conversation_history,
    )


__all__ = ("build_planner_context",)
