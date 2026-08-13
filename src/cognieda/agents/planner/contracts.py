from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_ai.messages import ModelMessage

from cognieda.schemas.artifacts import DataProfile, Discovery, Evidence, Objective
from cognieda.schemas.enums import AssumptionTestability


class PlannerAction(StrEnum):
    """Finite action space for the current routing-free Planner."""

    ANSWER_FROM_CONTEXT = "answer_from_context"
    SET_OR_REFINE_OBJECTIVE = "set_or_refine_objective"
    ASSESS_ASSUMPTION = "assess_assumption"
    STATE_SUMMARY = "state_summary"
    INVALID_OR_UNSUPPORTED = "invalid_or_unsupported"


class PlannerErrorCode(StrEnum):
    INVALID_COMMAND = "invalid_command"
    MODEL_UNAVAILABLE = "model_unavailable"
    INVALID_MODEL_DECISION = "invalid_model_decision"
    UNSUPPORTED_ACTION = "unsupported_action"
    INVALID_SUCCESSOR_STATE = "invalid_successor_state"
    NO_AUTHORITATIVE_SUPPORT = "no_authoritative_support"
    RESPONSE_FAILED = "response_failed"


class PlannerControlledError(BaseModel):
    """Application-facing failure that does not leak an arbitrary exception."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: PlannerErrorCode
    message: str = Field(min_length=1)


class AnswerFromContextDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    action: Literal[PlannerAction.ANSWER_FROM_CONTEXT] = (
        PlannerAction.ANSWER_FROM_CONTEXT
    )


class StateSummaryDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    action: Literal[PlannerAction.STATE_SUMMARY] = PlannerAction.STATE_SUMMARY


class SetOrRefineObjectiveDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    action: Literal[PlannerAction.SET_OR_REFINE_OBJECTIVE] = (
        PlannerAction.SET_OR_REFINE_OBJECTIVE
    )
    objective: Objective


class AssumptionAssessment(BaseModel):
    """Planner assessment of exact Human text; never an Assumption FCO."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_text: str = Field(min_length=1)
    testability: AssumptionTestability


class AssumptionAssessmentDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    action: Literal[PlannerAction.ASSESS_ASSUMPTION] = PlannerAction.ASSESS_ASSUMPTION
    assessment: AssumptionAssessment


class UnsupportedDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    action: Literal[PlannerAction.INVALID_OR_UNSUPPORTED] = (
        PlannerAction.INVALID_OR_UNSUPPORTED
    )
    message: str = Field(min_length=1)


type PlannerDecision = Annotated[
    AnswerFromContextDecision
    | StateSummaryDecision
    | SetOrRefineObjectiveDecision
    | AssumptionAssessmentDecision
    | UnsupportedDecision,
    Field(discriminator="action"),
]


class PlannerAnswerContext(BaseModel):
    """Authorized support for answer drafting; planning context is excluded."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    request: str = Field(min_length=1)
    objective: Objective | None = None
    data_profile: DataProfile | None = None
    evidences: tuple[Evidence, ...] = ()
    discoveries: tuple[Discovery, ...] = ()

    @model_validator(mode="after")
    def _has_authoritative_support(self) -> PlannerAnswerContext:
        if not self.evidences and not self.discoveries:
            raise ValueError(
                "Planner answer context requires admitted Evidence or governed Discovery."
            )
        return self


class PlannerResponseDraft(BaseModel):
    """Human-facing prose drafted only from an authorized answer context."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str = Field(min_length=1)


class PlannerOutput(BaseModel):
    """Application-relevant result for one Planner turn."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    response: str = Field(min_length=1)
    decision: PlannerDecision | None = None
    objective_proposal: Objective | None = None
    assumption_assessment: AssumptionAssessment | None = None
    new_messages: tuple[ModelMessage, ...] = ()
    error: PlannerControlledError | None = None
