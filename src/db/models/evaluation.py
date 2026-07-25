"""SQLModel table definitions for evaluation-owned records."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, CheckConstraint, Column, Index, Text, UniqueConstraint, text
from sqlmodel import Field

from db.models.common import TimestampedRecord
from schemas.enums import EvaluationControlState


class EvaluationControlRecord(TimestampedRecord, table=True):
    """Persisted non-FCO operational evaluation control record."""

    __tablename__ = "evaluation_controls"
    __table_args__ = (
        UniqueConstraint(
            "hypothesis_id",
            "bundle_digest",
            "contract_version",
            name="uq_evaluation_controls_bundle_identity",
        ),
        UniqueConstraint("evaluation_key", name="uq_evaluation_controls_evaluation_key"),
        Index(
            "uq_evaluation_controls_active_hypothesis",
            "hypothesis_id",
            unique=True,
            sqlite_where=text(
                "state IN ('PENDING', 'CLAIMED', 'PROPOSAL_READY', 'RETRYABLE_FAILED')"
            ),
        ),
        Index(
            "uq_evaluation_controls_proposal_digest",
            "proposal_digest",
            unique=True,
            sqlite_where=text("proposal_digest IS NOT NULL"),
        ),
        CheckConstraint(
            "fencing_epoch >= 0 AND attempt_number >= 1",
            name="ck_evaluation_controls_positive_fence_attempt",
        ),
        CheckConstraint(
            "state != 'CLAIMED' OR "
            "(owner IS NOT NULL AND claim_time IS NOT NULL AND claim_expiry IS NOT NULL)",
            name="ck_evaluation_controls_claim_authority",
        ),
        CheckConstraint(
            "state != 'PROPOSAL_READY' OR "
            "(proposal_digest IS NOT NULL AND serialized_proposal IS NOT NULL)",
            name="ck_evaluation_controls_proposal_provenance",
        ),
    )

    evaluation_id: UUID = Field(default_factory=uuid4, primary_key=True)
    hypothesis_id: UUID = Field(foreign_key="hypotheses.hypothesis_id", nullable=False, index=True)
    evidence_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    evidence_set_digest: str = Field(nullable=False, index=True)
    bundle_digest: str = Field(nullable=False, index=True)
    contract_version: str = Field(default="1.0", nullable=False)
    evaluation_key: str = Field(nullable=False, index=True)
    serialized_manifest: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    state: EvaluationControlState = Field(
        default=EvaluationControlState.PENDING, nullable=False, index=True
    )
    owner: str | None = Field(default=None, index=True)
    claim_time: datetime | None = Field(default=None)
    claim_expiry: datetime | None = Field(default=None)
    fencing_epoch: int = Field(default=0, nullable=False)
    attempt_number: int = Field(default=1, nullable=False)
    proposal_digest: str | None = Field(default=None, index=True)
    serialized_proposal: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )
    failure_reason: str | None = Field(default=None, index=True)
    serialized_failure: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )
    invalidation_reason: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
