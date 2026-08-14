from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_ai.messages import ModelMessage

from .context import PlannerContext
from .contracts import PlannerControlledError, PlannerResult


class PlannerState(BaseModel):
    """Per-run state spanning plan, Human review, and execute."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    request: str = Field(min_length=1)
    context: PlannerContext
    result: PlannerResult | None = None
    messages: tuple[ModelMessage, ...] = ()
    human_feedback: str | None = None
    execution_blocker: str | None = None
    error: PlannerControlledError | None = None

    @field_validator("result", mode="before")
    @classmethod
    def _revalidate_checkpointed_result(
        cls,
        value: object,
    ) -> object:
        if isinstance(value, PlannerResult):
            payload = value.model_dump(exclude_computed_fields=True, warnings=False)
            plan = payload.get("plan")
            if isinstance(plan, dict):
                plan.pop("fingerprint", None)
            return payload
        return value


__all__ = ("PlannerState",)
