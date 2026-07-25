"""Evidence provenance and AnalysisFrame schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from schemas.common import (
    CogniEDABaseModel,
    EvidenceProvenance,
    EvidenceResultSummary,
    NonEmptyStr,
    utc_now,
)
from schemas.enums import ValiditySourceState

__all__ = [
    "AnalysisFrame",
    "EvidenceProvenance",
    "EvidenceResultSummary",
]


class AnalysisFrame(CogniEDABaseModel):
    """Provenance pointer for the data view used by an analysis."""

    analysis_frame_id: UUID = Field(default_factory=uuid4)
    data_profile_id: UUID
    frame_hash: NonEmptyStr | None = None
    frame_ref: NonEmptyStr | None = None
    column_refs: list[NonEmptyStr] = Field(default_factory=list)
    row_filter_description: str | None = None
    validity_state: ValiditySourceState = ValiditySourceState.ACTIVE
    validity_reason: str | None = None
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _has_frame_identity(self) -> AnalysisFrame:
        """Require at least one stable way to identify the analysis view."""

        if self.frame_hash is None and self.frame_ref is None:
            raise ValueError("AnalysisFrame requires frame_hash or frame_ref.")
        return self
