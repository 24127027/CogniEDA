"""Canonical pre-persistence observations produced by scientific execution."""

from __future__ import annotations

from pydantic import Field, model_validator

from schemas.common import (
    CogniEDABaseModel,
    EvidenceResultSummary,
    MethodParameter,
    NonEmptyStr,
)
from schemas.enums import EvidenceType


class AnalysisFrameObservation(CogniEDABaseModel):
    """Observed analysis-view facts without durable AnalysisFrame identity."""

    frame_hash: NonEmptyStr | None = None
    frame_ref: NonEmptyStr | None = None
    column_refs: list[NonEmptyStr] = Field(default_factory=list)
    row_filter_description: str | None = None

    @model_validator(mode="after")
    def _has_frame_identity(self) -> AnalysisFrameObservation:
        if self.frame_hash is None and self.frame_ref is None:
            raise ValueError("Analysis frame observation requires frame_hash or frame_ref.")
        return self


class EvidenceObservation(CogniEDABaseModel):
    """Observed analytical result before immutable Evidence is admitted."""

    evidence_type: EvidenceType
    method: NonEmptyStr
    parameters: list[MethodParameter] = Field(default_factory=list)
    result_summary: EvidenceResultSummary
    artifact_refs: list[NonEmptyStr] = Field(default_factory=list)
    limitations: list[NonEmptyStr] = Field(default_factory=list)
    code_reference: str | None = None
    environment_reference: str | None = None
