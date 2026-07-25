"""Canonical Discovery and DiscoveryClaim schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from schemas.common import (
    DiscoveryClaim,
    ImmutableCogniEDABaseModel,
    NonEmptyStr,
    ValidityBasis,
    utc_now,
)
from schemas.enums import (
    AnalysisIntent,
    DiscoveryEpistemicStatus,
    DiscoveryLifecycleState,
)

__all__ = [
    "Discovery",
    "DiscoveryClaim",
]


class Discovery(ImmutableCogniEDABaseModel):
    """Evidence-bound claim produced from exactly one Hypothesis."""

    discovery_id: UUID = Field(default_factory=uuid4)
    hypothesis_id: UUID
    evidence_ids: list[UUID]
    claim: DiscoveryClaim
    epistemic_status: DiscoveryEpistemicStatus
    analysis_intent: AnalysisIntent = AnalysisIntent.EXPLORATORY
    uncertainty: str | None = None
    scope: NonEmptyStr
    validity_basis: ValidityBasis
    limitations: list[NonEmptyStr] = Field(default_factory=list)
    invalidators: list[NonEmptyStr] = Field(default_factory=list)
    lifecycle_state: DiscoveryLifecycleState = DiscoveryLifecycleState.ACTIVE
    review_reasons: list[NonEmptyStr] = Field(default_factory=list)
    flagged_by_evidence_ids: list[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _validate_evidence_bound_claim(self) -> Discovery:
        if not self.evidence_ids:
            raise ValueError("Discovery requires at least one Evidence reference.")
        if self.validity_basis.hypothesis_id != self.hypothesis_id:
            raise ValueError("Discovery validity_basis must reference the same Hypothesis.")
        if set(self.validity_basis.evidence_ids) != set(self.evidence_ids):
            raise ValueError("Discovery validity_basis must cover all supporting Evidence.")
        if self.validity_basis.assumptions_excluded_from_inference is not True:
            raise ValueError("Discovery inference must exclude Assumptions.")
        return self
