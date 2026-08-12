from __future__ import annotations

from cognieda.agents.planner.context import PlanningContext
from cognieda.agents.planner.types import PlannerOutput
from cognieda.schemas.artifacts import SessionFrame

from .conversation import ConversationHistory


def build_planning_context(
    session_frame: SessionFrame,
    conversation_history: ConversationHistory,
) -> PlanningContext:
    """Materialize every retained frame member without filtering or ranking."""

    return PlanningContext(
        objective=session_frame.objective,
        assumptions=session_frame.assumptions,
        tasks=session_frame.tasks,
        evidences=session_frame.evidences,
        data_profile=session_frame.data_profile,
        conversation_history=conversation_history,
    )


def apply_planner_output(
    current_frame: SessionFrame,
    planner_output: PlannerOutput,
) -> SessionFrame:
    """Apply the bounded typed results from one Planner turn to a successor frame."""

    successor = current_frame
    if planner_output.created_objective is not None:
        successor = successor.set_objective(planner_output.created_objective)
    if planner_output.created_assumption is not None:
        successor = successor.add_assumption(planner_output.created_assumption)
    return successor
