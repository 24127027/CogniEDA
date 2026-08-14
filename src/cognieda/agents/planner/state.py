from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_ai.messages import ModelMessage

from .context import PlannerContext
from .contracts import PlannerCognitiveResult, PlannerControlledError


class PlannerState(BaseModel):
    """Per-run state spanning plan, Human review, and execute."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    request: str = Field(min_length=1)
    context: PlannerContext
    cognitive_result: PlannerCognitiveResult | None = None
    messages: tuple[ModelMessage, ...] = ()
    approved_plan_id: UUID | None = None
    human_feedback: str | None = None
    error: PlannerControlledError | None = None

    @field_validator("cognitive_result", mode="before")
    @classmethod
    def _revalidate_checkpointed_result(
        cls,
        value: object,
    ) -> object:
        if isinstance(value, PlannerCognitiveResult):
            payload = value.model_dump(exclude_computed_fields=True, warnings=False)
            plan = payload.get("plan")
            if isinstance(plan, dict):
                plan.pop("fingerprint", None)
            return payload
        return value


__all__ = ("PlannerState",)
