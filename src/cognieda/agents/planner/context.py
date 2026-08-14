from __future__ import annotations

from pydantic import Field

from cognieda.runtime.conversation import ConversationHistory
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
    """Readable Planner input; conversation history inside it is non-authoritative."""

    active_plan: Plan | None = None
    objective: Objective | None = None
    assumptions: tuple[Assumption, ...] = ()
    tasks: tuple[Task, ...] = ()
    evidences: tuple[Evidence, ...] = ()
    discoveries: tuple[Discovery, ...] = ()
    data_profile: DataProfile | None = None
    conversation_history: ConversationHistory = Field(default_factory=ConversationHistory)


__all__ = ("PlannerContext",)
