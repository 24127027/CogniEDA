from __future__ import annotations

from dataclasses import dataclass

from pydantic_ai.messages import ModelMessage

from cognieda.schemas.artifacts import (
    Assumption,
    DataProfile,
    Discovery,
    Evidence,
    Hypothesis,
    Objective,
)
from cognieda.schemas.common import ImmutableCogniEDABaseModel


class PlannerContext(ImmutableCogniEDABaseModel):
    """Authoritative coordination and readable research state for one invocation."""

    objectives: tuple[Objective, ...] = ()
    assumptions: tuple[Assumption, ...] = ()
    hypotheses: tuple[Hypothesis, ...] = ()
    evidences: tuple[Evidence, ...] = ()
    discoveries: tuple[Discovery, ...] = ()
    data_profile: DataProfile | None = None


@dataclass(frozen=True)
class PlannerRunContext:
    """Run-scoped transport payload supplied to the compiled Planner graph."""

    planner_context: PlannerContext
    message_history: tuple[ModelMessage, ...] = ()


__all__ = (
    "PlannerContext",
    "PlannerRunContext",
)
