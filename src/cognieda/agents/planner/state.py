from __future__ import annotations

from typing import TypedDict

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_ai.messages import ModelMessage

from cognieda.schemas.plan import Plan

from .types import PlannerControlledError


class PlannerTurnOutcome(BaseModel):
    """Typed presentation facts produced by one Planner graph turn."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    proposed_plan: Plan | None = None
    response: str | None = Field(default=None, min_length=1)
    human_input_request: str | None = Field(default=None, min_length=1)
    error: PlannerControlledError | None = None

    @model_validator(mode="after")
    def _validate_coherence(self) -> PlannerTurnOutcome:
        if not any(
            (
                self.proposed_plan is not None,
                self.response is not None,
                self.human_input_request is not None,
                self.error is not None,
            )
        ):
            raise ValueError("PlannerTurnOutcome requires a visible or controlled result.")
        return self


class PlannerGraphInput(TypedDict):
    """Run-scoped input accepted by the compiled Planner graph."""

    latest_human_input: str


class PlannerGraphOutput(TypedDict):
    """Presentation facts returned by one compiled Planner graph invocation."""

    turn_outcome: PlannerTurnOutcome | None


class PlannerState(TypedDict):
    """Checkpointed Planner lifecycle state; never authoritative research state."""

    latest_human_input: str | None
    candidate_plan: Plan | None
    messages: tuple[ModelMessage, ...]
    turn_outcome: PlannerTurnOutcome | None


__all__ = (
    "PlannerGraphInput",
    "PlannerGraphOutput",
    "PlannerState",
    "PlannerTurnOutcome",
)

