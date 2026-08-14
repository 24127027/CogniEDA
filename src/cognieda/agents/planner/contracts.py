from __future__ import annotations

from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_ai.messages import ModelMessage

from cognieda.schemas.artifacts import Task
from cognieda.schemas.plan import Plan


class PlannerErrorCode(StrEnum):
    INVALID_COMMAND = "invalid_command"
    MODEL_UNAVAILABLE = "model_unavailable"
    INVALID_MODEL_RESULT = "invalid_model_result"
    INVALID_SUCCESSOR_STATE = "invalid_successor_state"
    RESPONSE_FAILED = "response_failed"


class PlannerControlledError(BaseModel):
    """Application-facing failure that does not leak an arbitrary exception."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: PlannerErrorCode
    message: str = Field(min_length=1)


class PlannerResult(BaseModel):
    """Typed reasoning result produced only by ``plan_or_answer``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    plan: Plan | None = None
    tasks: tuple[Task, ...] = ()
    response: str | None = Field(default=None, min_length=1)
    human_input_request: str | None = Field(default=None, min_length=1)
    continue_execution: bool = False

    @model_validator(mode="after")
    def _coherent_result(self) -> Self:
        if self.plan is None and self.tasks:
            raise ValueError("Planner Tasks require one candidate Plan.")
        if self.plan is not None:
            self.plan.validate_tasks(self.tasks)
            if self.human_input_request is not None:
                raise ValueError("A complete Plan cannot also request clarification.")
            if self.continue_execution:
                raise ValueError("A candidate Plan cannot also continue an active Plan.")
        if self.continue_execution and self.human_input_request is not None:
            raise ValueError("Execution cannot be requested with Human clarification.")
        if not any(
            (
                self.plan is not None,
                self.response is not None,
                self.human_input_request is not None,
                self.continue_execution,
            )
        ):
            raise ValueError("PlannerResult requires one meaningful result field.")
        return self


class PlanReviewAction(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    REVISE = "revise"


class PlanReviewDecision(BaseModel):
    """Exact Human authority supplied when resuming the approval interrupt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action: PlanReviewAction
    plan_id: UUID
    feedback: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _feedback_matches_action(self) -> Self:
        if self.action is PlanReviewAction.APPROVE and self.feedback is not None:
            raise ValueError("Approval does not accept revision feedback.")
        if self.action is not PlanReviewAction.APPROVE and self.feedback is None:
            raise ValueError("Rejection or revision requires explicit Human feedback.")
        return self


class PlannerOutput(BaseModel):
    """Application-facing envelope for one Planner lifecycle snapshot."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid", frozen=True)

    result: PlannerResult
    messages: tuple[ModelMessage, ...] = ()
    error: PlannerControlledError | None = None

    @property
    def response(self) -> str:
        result = self.result
        if result.response is not None:
            return result.response
        if result.human_input_request is not None:
            return result.human_input_request
        if result.plan is not None:
            return "A candidate Plan is ready for Human review."
        if result.continue_execution:
            return "Continuing the active approved Plan."
        if self.error is not None:
            return self.error.message
        return "Planner completed without a Human-facing response."


__all__ = (
    "PlannerResult",
    "PlannerControlledError",
    "PlannerErrorCode",
    "PlannerOutput",
    "PlanReviewAction",
    "PlanReviewDecision",
)
