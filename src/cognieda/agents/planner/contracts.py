from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_ai.messages import ModelMessage

from cognieda.schemas.artifacts import DataProfile, Discovery, Evidence, Objective
from cognieda.schemas.enums import AssumptionTestability


class PlannerErrorCode(StrEnum):
    INVALID_COMMAND = "invalid_command"
    MODEL_UNAVAILABLE = "model_unavailable"
    INVALID_MODEL_RESULT = "invalid_model_result"
    INVALID_SUCCESSOR_STATE = "invalid_successor_state"
    NO_AUTHORITATIVE_SUPPORT = "no_authoritative_support"
    RESPONSE_FAILED = "response_failed"


class PlannerControlledError(BaseModel):
    """Application-facing failure that does not leak an arbitrary exception."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: PlannerErrorCode
    message: str = Field(min_length=1)


class DirectResponse(BaseModel):
    """Human-facing result that proposes no authoritative state transition."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str = Field(min_length=1)


class ObjectiveProposal(BaseModel):
    """Canonical Objective proposed for validation by Application authority."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    objective: Objective
    response: str = Field(min_length=1)


class AssumptionAssessment(BaseModel):
    """Planner assessment of exact Human text; never an Assumption FCO."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_text: str = Field(min_length=1)
    testability: AssumptionTestability
    response: str = Field(min_length=1)


class AuthoritativeAnswerRequest(BaseModel):
    """Request drafting from the separate protected research-support context."""

    model_config = ConfigDict(extra="forbid", frozen=True)


type PlannerFinalResult = DirectResponse | ObjectiveProposal | AssumptionAssessment
type PlannerCognitiveResult = PlannerFinalResult | AuthoritativeAnswerRequest


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


class PlannerOutput(BaseModel):
    """Application-facing envelope for one completed Planner turn."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    result: PlannerFinalResult
    new_messages: tuple[ModelMessage, ...] = ()
    error: PlannerControlledError | None = None

    @property
    def response(self) -> str:
        if isinstance(self.result, DirectResponse):
            return self.result.text
        return self.result.response
