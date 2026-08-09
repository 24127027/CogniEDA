from pydantic import BaseModel, ConfigDict
from pydantic_ai import ModelMessage

from cognieda.schemas.artifacts import (
    Objective,
    Assumption,
    Task,
    Evidence,
    DataProfile
)
from cognieda.schemas.common import CogniEDABaseModel
from cognieda.runtime.conversation import ConversationHistory

class PlanningContext(CogniEDABaseModel):
    """Materialized research knowledge available to one Planner run."""

    objective: Objective | None = None
    assumptions: tuple[Assumption, ...] = ()
    tasks: tuple[Task, ...] = ()
    evidences: tuple[Evidence, ...] = ()
    data_profile: DataProfile | None = None

    conversation_history: ConversationHistory = ConversationHistory()

class Context(BaseModel):
    """Dependencies available to the Planner."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    planner_model: object | None = None
    planning_context: PlanningContext = PlanningContext()
