from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from cognieda.agents.planner.context import PlannerContext
from cognieda.schemas.artifacts import SessionFrame
from cognieda.schemas.plan import Plan


def build_planner_context(
    session_frame: SessionFrame,
    *,
    active_plans: tuple[Plan, ...] | Sequence[Plan] = (),
) -> PlannerContext:
    """Materialize retained readable state without filtering or authority changes."""

    plans = tuple(active_plans or ())
    frame_objective_ids = {obj.objective_id for obj in session_frame.objectives}

    seen_plan_ids: set[UUID] = set()
    seen_objective_ids: set[UUID] = set()

    for plan in plans:
        if plan.plan_id in seen_plan_ids:
            raise ValueError("build_planner_context rejects duplicate active Plan IDs.")
        seen_plan_ids.add(plan.plan_id)

        if plan.objective.objective_id not in frame_objective_ids:
            raise ValueError("Active Plan focal Objective must belong to the SessionFrame.")

        if plan.objective.objective_id in seen_objective_ids:
            raise ValueError(
                "build_planner_context rejects multiple active Plans for the same Objective."
            )
        seen_objective_ids.add(plan.objective.objective_id)

    return PlannerContext(
        active_plans=plans,
        objectives=session_frame.objectives,
        assumptions=session_frame.assumptions,
        hypotheses=session_frame.hypotheses,
        evidences=session_frame.evidences,
        discoveries=session_frame.discoveries,
        data_profile=session_frame.data_profile,
    )


__all__ = ("build_planner_context",)
