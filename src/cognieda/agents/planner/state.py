from __future__ import annotations

from typing import TypedDict

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_ai.messages import ModelMessage

from cognieda.schemas.artifacts import Task
from cognieda.schemas.plan import Plan

from .types import PlannerControlledError, PlannerResult


class PlannerTurnOutcome(BaseModel):
    """Typed presentation facts produced by one Planner graph turn."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_plan: Plan | None = None
    candidate_tasks: tuple[Task, ...] = ()
    response: str | None = Field(default=None, min_length=1)
    human_input_request: str | None = Field(default=None, min_length=1)
    candidate_admitted: bool = False
    candidate_discarded: bool = False
    active_plan_continuation_deferred: bool = False
    awaiting_human: bool = False
    error: PlannerControlledError | None = None

    @model_validator(mode="after")
    def _validate_coherence(self) -> PlannerTurnOutcome:
        if self.candidate_tasks and self.candidate_plan is None:
            raise ValueError("Outcome candidate Tasks require a candidate Plan.")
        if self.candidate_plan is not None:
            self.candidate_plan.validate_tasks(self.candidate_tasks)
        if not any(
            (
                self.candidate_plan is not None,
                self.response is not None,
                self.human_input_request is not None,
                self.candidate_admitted,
                self.candidate_discarded,
                self.active_plan_continuation_deferred,
                self.error is not None,
            )
        ):
            raise ValueError("PlannerTurnOutcome requires a visible or controlled result.")
        return self


class PlannerState(TypedDict):
    """Checkpointed Planner lifecycle state; never authoritative research state."""

    latest_human_input: str | None
    candidate_plan: Plan | None
    candidate_tasks: tuple[Task, ...]
    messages: tuple[ModelMessage, ...]
    result: PlannerResult | None
    error: PlannerControlledError | None
    turn_outcome: PlannerTurnOutcome | None


def empty_planner_state(latest_human_input: str | None = None) -> PlannerState:
    return PlannerState(
        latest_human_input=latest_human_input,
        candidate_plan=None,
        candidate_tasks=(),
        messages=(),
        result=None,
        error=None,
        turn_outcome=None,
    )


__all__ = ("PlannerState", "PlannerTurnOutcome", "empty_planner_state")
