from __future__ import annotations

from cognieda.agents.planner.context import PlanningContext
from cognieda.agents.planner.types import PlannerAction, PlannerOutput
from cognieda.schemas.artifacts import Assumption, SessionFrame

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
    *,
    human_request: str,
) -> SessionFrame:
    """Apply application-owned state changes from one Planner turn."""

    successor = current_frame
    if planner_output.created_objective is not None:
        successor = successor.set_objective(planner_output.created_objective)
    decision = planner_output.decision
    if decision is not None and decision.action is PlannerAction.ADD_ASSUMPTION:
        assumption_text = decision.assumption_text
        if (
            assumption_text is None
            or decision.assumption_is_reasonably_testable is not False
            or assumption_text not in human_request
        ):
            raise ValueError(
                "Assumption admission requires exact Human text classified as not "
                "reasonably testable."
            )
        successor = successor.add_assumption(Assumption(text=assumption_text))
    return successor
