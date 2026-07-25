"""Canonical Evidence domain schema."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from schemas.common import (
    ImmutableCogniEDABaseModel,
    MethodParameter,
    NonEmptyStr,
    utc_now,
)
from schemas.evidence.lifecycle import EvidenceLifecycleState, EvidenceType
from schemas.evidence.provenance import EvidenceProvenance, EvidenceResultSummary


class Evidence(ImmutableCogniEDABaseModel):
    """Directly observed analytical result, not interpretation."""

    evidence_id: UUID = Field(default_factory=uuid4)
    hypothesis_id: UUID
    profile_id: UUID
    analysis_frame_ref: NonEmptyStr
    execution_run_ref: NonEmptyStr
    evidence_type: EvidenceType
    method: NonEmptyStr
    parameters: list[MethodParameter] = Field(default_factory=list)
    provenance: EvidenceProvenance
    result_summary: EvidenceResultSummary
    artifact_refs: list[NonEmptyStr] = Field(default_factory=list)
    limitations: list[NonEmptyStr] = Field(default_factory=list)
    lifecycle_state: EvidenceLifecycleState = EvidenceLifecycleState.ACTIVE
    superseded_by_evidence_id: UUID | None = None
    lifecycle_reason: str | None = None
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _provenance_matches_required_refs(self) -> Evidence:
        if self.provenance.analysis_frame_ref != self.analysis_frame_ref:
            raise ValueError("Evidence provenance must reference the same AnalysisFrame.")
        if self.provenance.execution_run_ref != self.execution_run_ref:
            raise ValueError("Evidence provenance must reference the same ExecutionRun.")
        return self
