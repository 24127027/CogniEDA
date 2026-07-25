"""SQLModel table definitions for validity-owned records."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, Text, UniqueConstraint
from sqlmodel import Field

from db.models.common import TimestampedRecord, utc_now
from schemas.enums import AuthorizationClass, ValidityEventType, ValiditySourceType


class ValidityEventRecord(TimestampedRecord, table=True):
    """Persisted non-FCO durable validity event record."""

    __tablename__ = "validity_events"
    __table_args__ = (
        UniqueConstraint(
            "idempotency_key",
            name="uq_validity_events_idempotency_key",
        ),
        UniqueConstraint(
            "event_fingerprint",
            name="uq_validity_events_fingerprint",
        ),
    )

    event_id: UUID = Field(default_factory=uuid4, primary_key=True)
    source_type: ValiditySourceType = Field(nullable=False, index=True)
    source_id: UUID = Field(nullable=False, index=True)
    source_fingerprint: str | None = Field(default=None, index=True)
    event_type: ValidityEventType = Field(nullable=False, index=True)
    reason: str = Field(sa_column=Column(Text, nullable=False))
    authority_id: UUID = Field(
        foreign_key="governance_authorities.authority_id",
        nullable=False,
        index=True,
    )
    authority_identity: str = Field(nullable=False, index=True)
    authority_class: AuthorizationClass = Field(nullable=False, index=True)
    workspace_id: str = Field(nullable=False, index=True)
    session_id: str | None = Field(default=None, index=True)
    replacement_id: UUID | None = Field(default=None, index=True)
    replacement_fingerprint: str | None = Field(default=None, index=True)
    expected_source_state: str = Field(nullable=False)
    source_post_state: str = Field(nullable=False)
    idempotency_key: str = Field(nullable=False, index=True)
    event_fingerprint: str = Field(nullable=False, index=True)
    plan_fingerprint: str = Field(nullable=False, index=True)
    affected_targets: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    processing_state: str = Field(default="COMMITTED", nullable=False, index=True)
    committed_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)
