"""Planner-specific graph contracts."""

from pydantic import BaseModel, Field
from pydantic_ai.messages import ModelMessage

from agents.executor.types import ExecutionRequest


class State(BaseModel):
    """Internal Planner state."""

    query: str
    history: list[ModelMessage] = Field(default_factory=list)


class Context(BaseModel):
    """Context for the Planner agent."""


class PlannerOutput(BaseModel):
    """PydanticAI output schema for planner-authored requests."""


