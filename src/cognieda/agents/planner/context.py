from __future__ import annotations

from pydantic import Field, model_validator

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
    """Readable research state for one Planner cognitive invocation."""

    pending_plan: Plan | None = None
    pending_tasks: tuple[Task, ...] = ()
    active_plan: Plan | None = None
    objective: Objective | None = None
    assumptions: tuple[Assumption, ...] = ()
    tasks: tuple[Task, ...] = ()
    evidences: tuple[Evidence, ...] = ()
    discoveries: tuple[Discovery, ...] = ()
    data_profile: DataProfile | None = None
    conversation_history: ConversationHistory = Field(default_factory=ConversationHistory)

    @model_validator(mode="after")
    def _validate_pending_bundle(self) -> PlannerContext:
        if self.pending_tasks and self.pending_plan is None:
            raise ValueError("Pending Tasks require a pending Plan.")
        if self.pending_plan is not None:
            self.pending_plan.validate_tasks(self.pending_tasks)
        return self
