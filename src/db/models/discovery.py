"""SQLModel table definitions for Discovery-owned records."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, CheckConstraint, Column, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

from schemas.enums import (
    AnalysisIntent,
    DiscoveryAdmissionClaimState,
    DiscoveryEpistemicStatus,
    DiscoveryLifecycleState,
)


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp for persisted rows."""

    return datetime.now(UTC)


class TimestampedRecord(SQLModel):
    """Shared timestamp fields for persisted rows with lifecycle transitions."""

    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)


class DiscoveryRecord(SQLModel, table=True):
    """Persisted immutable Discovery FCO."""

    __tablename__ = "discoveries"
    __table_args__ = (UniqueConstraint("hypothesis_id", name="uq_discoveries_hypothesis_id"),)

    discovery_id: UUID = Field(default_factory=uuid4, primary_key=True)
    hypothesis_id: UUID = Field(foreign_key="hypotheses.hypothesis_id", nullable=False, index=True)
    evidence_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    claim: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    epistemic_status: DiscoveryEpistemicStatus = Field(nullable=False, index=True)
    analysis_intent: AnalysisIntent = Field(
        default=AnalysisIntent.EXPLORATORY, nullable=False, index=True
    )
    uncertainty: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    scope: str = Field(sa_column=Column(Text, nullable=False))
    validity_basis: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    limitations: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    invalidators: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    lifecycle_state: DiscoveryLifecycleState = Field(
        default=DiscoveryLifecycleState.ACTIVE,
        nullable=False,
        index=True,
    )
    review_reasons: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    flagged_by_evidence_ids: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)


class DiscoveryAdmissionClaimRecord(TimestampedRecord, table=True):
    """Persisted non-FCO operational admission claim record."""

    __tablename__ = "discovery_admission_claims"
    __table_args__ = (
        UniqueConstraint(
            "evaluation_id",
            name="uq_discovery_admission_claims_evaluation",
        ),
        UniqueConstraint(
            "admission_fingerprint",
            name="uq_discovery_admission_claims_fingerprint",
        ),
        UniqueConstraint(
            "decision_id",
            name="uq_discovery_admission_claims_decision",
        ),
        CheckConstraint(
            "fencing_epoch >= 0 AND attempt_number >= 1",
            name="ck_discovery_admission_claims_positive_fence_attempt",
        ),
        CheckConstraint(
            "state != 'CLAIMED' OR "
            "(owner IS NOT NULL AND claim_time IS NOT NULL AND claim_expiry IS NOT NULL "
            "AND claim_token_digest IS NOT NULL)",
            name="ck_discovery_admission_claims_claim_authority",
        ),
        CheckConstraint(
            "state != 'COMMITTED' OR "
            "(discovery_id IS NOT NULL AND discovery_fingerprint IS NOT NULL "
            "AND session_frame_id IS NOT NULL AND session_frame_fingerprint IS NOT NULL "
            "AND committed_at IS NOT NULL)",
            name="ck_discovery_admission_claims_committed_chain",
        ),
    )

    claim_id: UUID = Field(default_factory=uuid4, primary_key=True)
    evaluation_id: UUID = Field(
        foreign_key="evaluation_controls.evaluation_id", nullable=False, index=True
    )
    decision_id: UUID = Field(
        foreign_key="proposal_decisions.decision_id", nullable=False, index=True
    )
    proposal_digest: str = Field(nullable=False, index=True)
    bundle_digest: str = Field(nullable=False, index=True)
    admission_fingerprint: str = Field(nullable=False, index=True)
    owner: str | None = Field(default=None, index=True)
    claim_time: datetime | None = Field(default=None)
    claim_expiry: datetime | None = Field(default=None)
    claim_token_digest: str | None = Field(default=None)
    fencing_epoch: int = Field(default=0, nullable=False)
    attempt_number: int = Field(default=1, nullable=False)
    state: DiscoveryAdmissionClaimState = Field(
        default=DiscoveryAdmissionClaimState.PENDING, nullable=False, index=True
    )
    discovery_id: UUID | None = Field(
        default=None,
        foreign_key="discoveries.discovery_id",
        index=True,
    )
    discovery_fingerprint: str | None = Field(default=None, index=True)
    session_frame_id: UUID | None = Field(
        default=None,
        foreign_key="session_frames.session_frame_id",
        index=True,
    )
    session_frame_fingerprint: str | None = Field(default=None, index=True)
    committed_at: datetime | None = Field(default=None, index=True)
    invalidation_reason: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
