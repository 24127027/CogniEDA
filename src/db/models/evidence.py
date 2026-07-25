"""SQLModel table definitions for Evidence-owned records."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, Text
from sqlmodel import Field, SQLModel

from db.models.common import utc_now
from schemas.enums import EvidenceLifecycleState, EvidenceType, ValiditySourceState


class AnalysisFrameRecord(SQLModel, table=True):
    """Minimal provenance record for the data view used by an analysis."""

    __tablename__ = "analysis_frames"

    analysis_frame_id: UUID = Field(default_factory=uuid4, primary_key=True)
    data_profile_id: UUID = Field(
        foreign_key="data_profiles.profile_id",
        nullable=False,
        index=True,
    )
    frame_hash: str | None = Field(default=None, index=True)
    frame_ref: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    column_refs: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    row_filter_description: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    validity_state: ValiditySourceState = Field(
        default=ValiditySourceState.ACTIVE,
        nullable=False,
        index=True,
    )
    validity_reason: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)


class EvidenceRecord(SQLModel, table=True):
    """Persisted immutable Evidence FCO."""

    __tablename__ = "evidence"

    evidence_id: UUID = Field(default_factory=uuid4, primary_key=True)
    hypothesis_id: UUID = Field(foreign_key="hypotheses.hypothesis_id", nullable=False, index=True)
    profile_id: UUID = Field(foreign_key="data_profiles.profile_id", nullable=False, index=True)
    analysis_frame_ref: str = Field(sa_column=Column(Text, nullable=False))
    execution_run_ref: str = Field(sa_column=Column(Text, nullable=False))
    evidence_type: EvidenceType = Field(nullable=False, index=True)
    method: str = Field(sa_column=Column(Text, nullable=False))
    parameters: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    provenance: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    result_summary: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    artifact_refs: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    limitations: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    lifecycle_state: EvidenceLifecycleState = Field(
        default=EvidenceLifecycleState.ACTIVE,
        nullable=False,
        index=True,
    )
    superseded_by_evidence_id: UUID | None = Field(
        default=None,
        foreign_key="evidence.evidence_id",
        index=True,
    )
    lifecycle_reason: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)
