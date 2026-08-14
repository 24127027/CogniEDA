from __future__ import annotations

from cognieda.agents.planner.context import PlannerContext
from cognieda.runtime.conversation import ConversationHistory
from cognieda.schemas.artifacts import SessionFrame
from cognieda.schemas.plan import Plan


def build_planner_context(
    session_frame: SessionFrame,
    conversation_history: ConversationHistory,
    *,
    active_plan: Plan | None = None,
) -> PlannerContext:
    """Materialize every retained frame member without filtering or ranking."""

    return PlannerContext(
        active_plan=active_plan,
        objective=session_frame.objective,
        assumptions=session_frame.assumptions,
        tasks=session_frame.tasks,
        evidences=session_frame.evidences,
        discoveries=session_frame.discoveries,
        data_profile=session_frame.data_profile,
        conversation_history=conversation_history,
    )
