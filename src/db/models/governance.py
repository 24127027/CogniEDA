"""SQLModel table definitions for governance-owned records."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Column, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

from schemas.enums import AuthorizationClass, GovernanceDecisionOutcome


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp for persisted rows."""

    return datetime.now(UTC)


class TimestampedRecord(SQLModel):
    """Shared timestamp fields for persisted rows with lifecycle transitions."""

    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)


class GovernanceAuthorityRecord(TimestampedRecord, table=True):
    """Durable non-FCO authority issued outside proposal-decision submission."""

    __tablename__ = "governance_authorities"
    __table_args__ = (
        UniqueConstraint(
            "authority_fingerprint",
            name="uq_governance_authorities_fingerprint",
        ),
        CheckConstraint(
            "authority_class != 'UNAUTHORIZED'",
            name="ck_governance_authorities_authorized_class",
        ),
        CheckConstraint(
            "authority_class != 'USER_GOVERNED' OR session_id IS NOT NULL",
            name="ck_governance_authorities_user_session",
        ),
    )

    authority_id: UUID = Field(default_factory=uuid4, primary_key=True)
    actor_identity: str = Field(nullable=False, index=True)
    authority_class: AuthorizationClass = Field(nullable=False, index=True)
    workspace_id: str = Field(nullable=False, index=True)
    session_id: str | None = Field(default=None, index=True)
    purpose: str = Field(nullable=False, index=True)
    operation_type: str = Field(nullable=False, index=True)
    issued_by: str = Field(nullable=False, index=True)
    issued_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)
    expires_at: datetime | None = Field(default=None, index=True)
    active: bool = Field(default=True, nullable=False, index=True)
    authority_fingerprint: str = Field(nullable=False, index=True)


class ProposalDecisionRecord(TimestampedRecord, table=True):
    """Persisted non-FCO governance decision record for an evaluation proposal."""

    __tablename__ = "proposal_decisions"
    __table_args__ = (
        UniqueConstraint(
            "evaluation_id",
            name="uq_proposal_decisions_evaluation",
        ),
        UniqueConstraint(
            "decision_fingerprint",
            name="uq_proposal_decisions_fingerprint",
        ),
        CheckConstraint(
            "(consumed = 0 AND consumed_at IS NULL AND consumed_by IS NULL) OR "
            "(consumed = 1 AND consumed_at IS NOT NULL AND consumed_by IS NOT NULL)",
            name="ck_proposal_decisions_consumption",
        ),
    )

    decision_id: UUID = Field(default_factory=uuid4, primary_key=True)
    authority_id: UUID = Field(
        foreign_key="governance_authorities.authority_id", nullable=False, index=True
    )
    evaluation_id: UUID = Field(
        foreign_key="evaluation_controls.evaluation_id", nullable=False, index=True
    )
    evaluation_key: str = Field(nullable=False, index=True)
    hypothesis_id: UUID = Field(foreign_key="hypotheses.hypothesis_id", nullable=False, index=True)
    task_id: UUID = Field(foreign_key="tasks.task_id", nullable=False, index=True)
    proposal_digest: str = Field(nullable=False, index=True)
    bundle_digest: str = Field(nullable=False, index=True)
    evidence_set_digest: str = Field(nullable=False, index=True)
    decision: GovernanceDecisionOutcome = Field(nullable=False, index=True)
    actor: str = Field(nullable=False, index=True)
    actor_authority_type: AuthorizationClass = Field(nullable=False, index=True)
    workspace_id: str = Field(nullable=False, index=True)
    session_id: str | None = Field(default=None, index=True)
    purpose: str = Field(nullable=False, index=True)
    operation_type: str = Field(nullable=False, index=True)
    decision_timestamp: datetime = Field(default_factory=utc_now, nullable=False, index=True)
    reason: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    decision_fingerprint: str = Field(nullable=False, index=True)
    consumed: bool = Field(default=False, nullable=False, index=True)
    consumed_at: datetime | None = Field(default=None)
    consumed_by: str | None = Field(default=None)
