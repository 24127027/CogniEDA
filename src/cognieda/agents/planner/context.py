from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from cognieda.runtime.conversation import ConversationHistory
from cognieda.schemas.artifacts import Assumption, DataProfile, Evidence, Objective, Task
from cognieda.schemas.common import CogniEDABaseModel


class PlanningContext(CogniEDABaseModel):
    """Materialized research knowledge and conversation available to one Planner run."""

    objective: Objective | None = None
    assumptions: tuple[Assumption, ...] = ()
    tasks: tuple[Task, ...] = ()
    evidences: tuple[Evidence, ...] = ()
    data_profile: DataProfile | None = None
    conversation_history: ConversationHistory = Field(default_factory=ConversationHistory)


class Context(BaseModel):
    """Injected dependencies and PlanningContext available to Planner graph nodes."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    planner_model: object
    dispatcher: object
    planning_context: PlanningContext = Field(default_factory=PlanningContext)
