"""Canonical Assumption research schema."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from schemas.common import CogniEDABaseModel, NonEmptyStr, utc_now
from schemas.enums import (
    AnalysisIntent,
    AssumptionSource,
    AssumptionStatus,
    AssumptionTestability,
    ConfidenceLevel,
)


class Assumption(CogniEDABaseModel):
    """Provisional analytical statement used for planning, not inference."""

    assumption_id: UUID = Field(default_factory=uuid4)
    statement: NonEmptyStr
    analysis_intent: AnalysisIntent = AnalysisIntent.EXPLORATORY
    scope: NonEmptyStr
    source: AssumptionSource = AssumptionSource.USER
    testability: AssumptionTestability = AssumptionTestability.UNTESTABLE_IN_PROJECT
    basis: NonEmptyStr | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    status: AssumptionStatus = AssumptionStatus.ACTIVE
    scoped_data_profile_ids: list[UUID] = Field(default_factory=list)
    contradicted_by_discovery_ids: list[UUID] = Field(default_factory=list)
    replacement_assumption_id: UUID | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _reject_testable_claim_as_assumption(self) -> Assumption:
        if self.testability == AssumptionTestability.TESTABLE_CLAIM_REJECTED_AS_ASSUMPTION:
            raise ValueError(
                "Testable claims must become Task/Hypothesis candidates, not Assumptions."
            )
        return self
