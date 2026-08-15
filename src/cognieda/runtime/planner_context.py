from __future__ import annotations

from dataclasses import dataclass

from cognieda.agents.planner.context import PlannerContext
from cognieda.infrastructure.persistence.repositories import (
    ActivePlanRepository,
    SessionFrameRepository,
)
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


@dataclass(frozen=True)
class PlannerContextProvider:
    """Materialize fresh Planner-readable authority for each cognitive invocation."""

    session_frames: SessionFrameRepository
    active_plans: ActivePlanRepository

    def materialize(self) -> PlannerContext:
        session_frame = self.session_frames.get_current()
        active_plan = None
        if session_frame.objective is not None:
            active_plan = self.active_plans.get_by_objective_id(
                session_frame.objective.objective_id
            )
        return build_planner_context(session_frame, active_plan=active_plan)
__all__ = (
    "PlannerContextProvider",
    "build_planner_context",
)
