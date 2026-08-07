from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class PlannedStep(BaseModel):
    """One bounded step proposed by the Planner."""

    title: str
    description: str
    capability: str | None = None


class PlannerPlan(BaseModel):
    """Planner output for one user request."""

    response_type: Literal["answer", "plan"]

    answer: str | None = None
    steps: list[PlannedStep] = Field(default_factory=list)


class State(BaseModel):
    """Transient state for one Planner invocation."""

    query: str
    plan: PlannerPlan | None = None
    error: str | None = None


class Context(BaseModel):
    """Dependencies available to the Planner."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    planner_model: object | None = None


class PlannerOutput(BaseModel):
    """Application-facing Planner result."""

    plan: PlannerPlan | None = None
    error: str | None = None