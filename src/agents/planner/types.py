"""Planner-specific graph contracts."""

from pydantic_ai.messages import ModelMessage
from pydantic import Field, BaseModel

class State(BaseModel):
    """Internal Planner state."""
    query: str
    history: list[ModelMessage] = Field(default_factory=list)
class Context(BaseModel):
    """Context for the Planner agent."""
