from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from cognieda.agents.planner.context import PlannerContext
from cognieda.infrastructure.persistence.repositories import ActivePlanRepository
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

    session_frame_provider: Callable[[], SessionFrame]
    active_plans: ActivePlanRepository

    def materialize(self) -> PlannerContext:
        session_frame = self.session_frame_provider()
        active_plan = None
        if session_frame.objective is not None:
            active_plan = self.active_plans.get_by_objective_id(
                session_frame.objective.objective_id
            )
        return build_planner_context(session_frame, active_plan=active_plan)


@dataclass
class SessionFrameState:
    """Mutable runtime holder for the current immutable SessionFrame value."""

    current: SessionFrame = field(default_factory=SessionFrame)

    def __call__(self) -> SessionFrame:
        return self.current


__all__ = (
    "PlannerContextProvider",
    "SessionFrameState",
    "build_planner_context",
)
