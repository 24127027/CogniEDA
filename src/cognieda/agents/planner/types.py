from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_ai.messages import ModelMessage

from cognieda.schemas.plan import Plan


class PlannerErrorCode(StrEnum):
    """Controlled failure categories for one Planner invocation."""

    INVALID_REQUEST = "invalid_request"
    MODEL_UNAVAILABLE = "model_unavailable"
    INVALID_MODEL_RESULT = "invalid_model_result"
    INVALID_LIFECYCLE_STATE = "invalid_lifecycle_state"
    PLAN_ADMISSION_FAILED = "plan_admission_failed"


class PlannerControlledError(BaseModel):
    """Application-facing failure without arbitrary exception details."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: PlannerErrorCode
    message: str = Field(min_length=1)


class PlannerResult(BaseModel):
    """One semantic conclusion produced by the Planner model."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    plan: Plan | None = None
    response: str | None = Field(default=None, min_length=1)
    human_input_request: str | None = Field(default=None, min_length=1)
    continue_execution: bool = False
    discard_candidate: bool = False

    @model_validator(mode="after")
    def _validate_coherence(self) -> PlannerResult:
        if self.continue_execution and self.plan is not None:
            raise ValueError(
                "continue_execution cannot accompany a new candidate Plan."
            )
        if self.continue_execution and self.human_input_request is not None:
            raise ValueError(
                "continue_execution cannot accompany a Human input request."
            )
        if self.discard_candidate and self.plan is not None:
            raise ValueError("discard_candidate cannot accompany a new candidate Plan.")
        if self.discard_candidate and self.continue_execution:
            raise ValueError("discard_candidate cannot accompany continue_execution.")
        if self.discard_candidate and self.human_input_request is not None:
            raise ValueError("discard_candidate cannot accompany a Human input request.")
        if not any(
            (
                self.plan is not None,
                self.response is not None,
                self.human_input_request is not None,
                self.continue_execution,
                self.discard_candidate,
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
