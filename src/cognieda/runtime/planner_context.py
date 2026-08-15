from __future__ import annotations

from cognieda.agents.planner.context import PlannerContext
from cognieda.schemas.artifacts import SessionFrame
from cognieda.schemas.plan import Plan


def build_planner_context(
    session_frame: SessionFrame,
    *,
    active_plan: Plan | None = None,
) -> PlannerContext:
    """Materialize retained readable state without filtering or authority changes."""

    if active_plan is not None and active_plan.objective != session_frame.objective:
        raise ValueError("Active Plan must match the exact SessionFrame Objective.")
    return PlannerContext(
        active_plan=active_plan,
        objective=session_frame.objective,
        assumptions=session_frame.assumptions,
        hypotheses=session_frame.hypotheses,
        evidences=session_frame.evidences,
        discoveries=session_frame.discoveries,
        data_profile=session_frame.data_profile,
    )


__all__ = ("build_planner_context",)
