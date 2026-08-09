from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field
from pydantic_ai.messages import ModelMessage

"""Graph contracts and transient state for the Planner agent."""

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

    new_messages: tuple[ModelMessage, ...] = ()

    error: str | None = None


class PlannerOutput(BaseModel):
    """Application-facing Planner result."""

    plan: PlannerPlan | None = None
    new_messages: tuple[ModelMessage, ...] = ()
    error: str | None = None