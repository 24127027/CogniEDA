from __future__ import annotations

from cognieda.schemas.artifacts import (
    Assumption,
    DataProfile,
    Discovery,
    Evidence,
    Objective,
    Task,
)
from cognieda.schemas.common import ImmutableCogniEDABaseModel
from cognieda.schemas.plan import Plan


class PlannerContext(ImmutableCogniEDABaseModel):
    """Readable research state for one Planner cognitive invocation."""

    active_plan: Plan | None = None
    objective: Objective | None = None
    assumptions: tuple[Assumption, ...] = ()
    tasks: tuple[Task, ...] = ()
    evidences: tuple[Evidence, ...] = ()
    discoveries: tuple[Discovery, ...] = ()
    data_profile: DataProfile | None = None
