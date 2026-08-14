from __future__ import annotations

from cognieda.agents.planner.context import PlannerContext
from cognieda.runtime.conversation import ConversationHistory
from cognieda.schemas.artifacts import SessionFrame


def build_planner_context(
    session_frame: SessionFrame,
    conversation_history: ConversationHistory,
) -> PlannerContext:
    """Materialize retained readable state without filtering or authority changes."""

    return PlannerContext(
        active_plan=None,
        objective=session_frame.objective,
        assumptions=session_frame.assumptions,
        tasks=session_frame.tasks,
        evidences=session_frame.evidences,
        discoveries=session_frame.discoveries,
        data_profile=session_frame.data_profile,
        conversation_history=conversation_history,
    )


__all__ = ("build_planner_context",)
