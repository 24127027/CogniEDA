from __future__ import annotations

from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_ai.messages import ModelMessage

from cognieda.schemas.artifacts import Task
from cognieda.schemas.enums import AssumptionTestability
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


class AssumptionAssessment(BaseModel):
    """Planner assessment of exact Human text; never an Assumption FCO."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_text: str = Field(min_length=1)
    testability: AssumptionTestability


class PlannerCognitiveResult(BaseModel):
    """One typed cognitive result shared by the plan and execute phases."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    plan: Plan | None = None
    tasks: tuple[Task, ...] = ()
    response: str | None = Field(default=None, min_length=1)
    human_input_request: str | None = Field(default=None, min_length=1)
    replan_reason: str | None = Field(default=None, min_length=1)
    assumption_assessment: AssumptionAssessment | None = None

    @model_validator(mode="after")
    def _coherent_result(self) -> Self:
        if self.plan is None and self.tasks:
            raise ValueError("Planner Tasks require one candidate Plan.")
        if self.plan is not None:
            self.plan.validate_tasks(self.tasks)
            if self.human_input_request is not None:
                raise ValueError("A complete Plan cannot also request clarification.")
            if self.replan_reason is not None:
                raise ValueError("A candidate Plan cannot also request replanning.")
            if self.assumption_assessment is not None:
                raise ValueError(
                    "A candidate Assumption assessment must be admitted before planning."
                )
        if self.replan_reason is not None and self.human_input_request is not None:
            raise ValueError("A result cannot request replanning and Human clarification.")
        if not any(
            (
                self.plan is not None,
                self.response is not None,
                self.human_input_request is not None,
                self.replan_reason is not None,
                self.assumption_assessment is not None,
            )
        ):
            raise ValueError("PlannerCognitiveResult requires one meaningful result field.")
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

    cognitive_result: PlannerCognitiveResult
    messages: tuple[ModelMessage, ...] = ()
    error: PlannerControlledError | None = None

    @property
    def response(self) -> str:
        result = self.cognitive_result
        if result.response is not None:
            return result.response
        if result.human_input_request is not None:
            return result.human_input_request
        if result.plan is not None:
            return "A candidate Plan is ready for Human review."
        if result.replan_reason is not None:
            return result.replan_reason
        if self.error is not None:
            return self.error.message
        return "Planner completed without a Human-facing response."


__all__ = (
    "AssumptionAssessment",
    "PlannerCognitiveResult",
    "PlannerControlledError",
    "PlannerErrorCode",
    "PlannerOutput",
    "PlanReviewAction",
    "PlanReviewDecision",
)
