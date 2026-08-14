from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_ai.messages import ModelMessage

from cognieda.schemas.artifacts import Task
from cognieda.schemas.plan import Plan


class PlannerErrorCode(StrEnum):
    """Controlled failure categories for one Planner invocation."""

    INVALID_REQUEST = "invalid_request"
    MODEL_UNAVAILABLE = "model_unavailable"
    INVALID_MODEL_RESULT = "invalid_model_result"


class PlannerControlledError(BaseModel):
    """Application-facing failure without arbitrary exception details."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: PlannerErrorCode
    message: str = Field(min_length=1)


class PlannerResult(BaseModel):
    """One semantic conclusion produced by the Planner model."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    plan: Plan | None = None
    tasks: tuple[Task, ...] = ()
    response: str | None = Field(default=None, min_length=1)
    human_input_request: str | None = Field(default=None, min_length=1)
    continue_execution: bool = False

    @model_validator(mode="after")
    def _validate_coherence(self) -> PlannerResult:
        if self.tasks and self.plan is None:
            raise ValueError("PlannerResult tasks require a candidate Plan.")
        if self.plan is not None:
            self.plan.validate_tasks(self.tasks)
        if self.continue_execution and self.plan is not None:
            raise ValueError(
                "continue_execution cannot accompany a new candidate Plan."
            )
        if self.continue_execution and self.human_input_request is not None:
            raise ValueError(
                "continue_execution cannot accompany a Human input request."
            )
        if not any(
            (
                self.plan is not None,
                self.response is not None,
                self.human_input_request is not None,
                self.continue_execution,
            )
        ):
            raise ValueError("PlannerResult must contain a meaningful conclusion.")
        return self


class PlannerOutput(BaseModel):
    """Runtime envelope for one Planner cognitive invocation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    result: PlannerResult
    messages: tuple[ModelMessage, ...] = ()
    error: PlannerControlledError | None = None


__all__ = (
    "PlannerControlledError",
    "PlannerErrorCode",
    "PlannerOutput",
    "PlannerResult",
)
