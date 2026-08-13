from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai.messages import ModelMessage

from cognieda.schemas.artifacts import Objective

from .contracts import (
    AssumptionAssessment,
    PlannerControlledError,
    PlannerDecision,
)


class PlannerState(BaseModel):
    """Per-run transient state for one Planner/LangGraph invocation."""

    model_config = ConfigDict(extra="forbid")

    request: str = Field(min_length=1)
    decision: PlannerDecision | None = None
    objective_proposal: Objective | None = None
    assumption_assessment: AssumptionAssessment | None = None
    response: str | None = None
    new_messages: tuple[ModelMessage, ...] = ()
    error: PlannerControlledError | None = None
