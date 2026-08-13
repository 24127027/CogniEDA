from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai.messages import ModelMessage

from .contracts import PlannerCognitiveResult, PlannerControlledError


class PlannerState(BaseModel):
    """Per-run transient state for one Planner/LangGraph invocation."""

    model_config = ConfigDict(extra="forbid")

    request: str = Field(min_length=1)
    result: PlannerCognitiveResult | None = None
    new_messages: tuple[ModelMessage, ...] = ()
    error: PlannerControlledError | None = None
