from __future__ import annotations

from cognieda.agents.planner.context import PlannerContext
from cognieda.agents.planner.contracts import (
    AssumptionAssessment,
    ObjectiveProposal,
    PlannerOutput,
)
from cognieda.schemas.artifacts import Assumption, SessionFrame
from cognieda.schemas.enums import AssumptionTestability


def build_planner_context(session_frame: SessionFrame) -> PlannerContext:
    """Materialize every retained frame member without filtering or ranking."""

    return PlannerContext(
        objective=session_frame.objective,
        assumptions=session_frame.assumptions,
        tasks=session_frame.tasks,
        evidences=session_frame.evidences,
        discoveries=session_frame.discoveries,
        data_profile=session_frame.data_profile,
    )


def apply_planner_output(
    current_frame: SessionFrame,
    planner_output: PlannerOutput,
    *,
    request: str,
) -> SessionFrame:
    """Apply the bounded typed results from one Planner turn to a successor frame."""

    successor = current_frame
    result = planner_output.result
    if isinstance(result, ObjectiveProposal):
        successor = successor.set_objective(result.objective)
    if isinstance(result, AssumptionAssessment):
        if result.source_text != request:
            raise ValueError("Planner Assumption assessment must preserve exact Human text.")
        if result.testability is AssumptionTestability.UNTESTABLE_IN_PROJECT:
            successor = successor.add_assumption(Assumption(text=result.source_text))
    return successor
