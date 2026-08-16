from __future__ import annotations

from cognieda.agents.planner.context import PlannerContext
from cognieda.schemas.artifacts import SessionFrame


def build_planner_context(
    session_frame: SessionFrame,
) -> PlannerContext:
    """Materialize retained readable state without filtering or authority changes."""

    return PlannerContext(
        objectives=session_frame.objectives,
        assumptions=session_frame.assumptions,
        hypotheses=session_frame.hypotheses,
        evidences=session_frame.evidences,
        discoveries=session_frame.discoveries,
        data_profile=session_frame.data_profile,
    )


__all__ = ("build_planner_context",)
