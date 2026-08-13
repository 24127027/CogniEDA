from __future__ import annotations

from pydantic import BaseModel, ConfigDict

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


class PlannerContext(ImmutableCogniEDABaseModel):
    """Exact read-only materialization of retained authorized research state."""

    objective: Objective | None = None
    assumptions: tuple[Assumption, ...] = ()
    tasks: tuple[Task, ...] = ()
    evidences: tuple[Evidence, ...] = ()
    discoveries: tuple[Discovery, ...] = ()
    data_profile: DataProfile | None = None


class Context(BaseModel):
    """Injected non-transient dependencies available to Planner graph nodes."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    agent: object
    planner_context: PlannerContext
    conversation_history: ConversationHistory
    decide_instructions: tuple[str, ...]
    answer_instructions: tuple[str, ...]
