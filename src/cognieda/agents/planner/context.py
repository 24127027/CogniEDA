from __future__ import annotations

from cognieda.schemas.artifacts import (
    Assumption,
    DataProfile,
    Discovery,
    Evidence,
    Hypothesis,
    Objective,
)
from cognieda.schemas.common import ImmutableCogniEDABaseModel
from cognieda.schemas.plan import Plan


class PlannerContext(ImmutableCogniEDABaseModel):
    """Authoritative coordination and readable research state for one invocation."""

    active_plan: Plan | None = None
    objective: Objective | None = None
    assumptions: tuple[Assumption, ...] = ()
    hypotheses: tuple[Hypothesis, ...] = ()
    evidences: tuple[Evidence, ...] = ()
    discoveries: tuple[Discovery, ...] = ()
    data_profile: DataProfile | None = None
