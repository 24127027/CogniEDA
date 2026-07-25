"""Canonical Hypothesis research schema."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import Field

from schemas.common import CogniEDABaseModel, NonEmptyStr, utc_now
from schemas.enums import AnalysisIntent, HypothesisStatus


class Hypothesis(CogniEDABaseModel):
    """Atomic test contract created from one terminal analytical Task."""

    hypothesis_id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    profile_id: UUID
    statement: NonEmptyStr
    analysis_intent: AnalysisIntent = AnalysisIntent.EXPLORATORY
    variables: list[NonEmptyStr] = Field(default_factory=list)
    scope: NonEmptyStr
    validation_method: NonEmptyStr
    evidence_expectation: NonEmptyStr
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    review_reasons: list[NonEmptyStr] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
