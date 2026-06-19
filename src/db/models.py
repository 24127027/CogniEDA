"""SQLModel table definitions for persisted CogniEDA artifacts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, Text
from sqlmodel import Field, SQLModel

from schemas.enums import (
    AssumptionStatus,
    ConfidenceLevel,
    DataProfileMethod,
    DatasetKind,
    DatasetRole,
    DatasetSourceType,
    DecisionStatus,
    DecisionType,
    EvidenceType,
    HypothesisStatus,
    ProjectStatus,
)


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp for persisted rows."""

    return datetime.now(UTC)


class TimestampedRecord(SQLModel):
    """Shared timestamp fields for persisted artifact records."""

    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)


class ProjectRecord(TimestampedRecord, table=True):
    """Persisted project artifact."""

    __tablename__ = "projects"

    project_id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True, min_length=1, nullable=False)
    objective: str = Field(sa_column=Column(Text, nullable=False))
    research_questions: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    status: ProjectStatus = Field(default=ProjectStatus.ACTIVE, nullable=False, index=True)


class DatasetAssetRecord(TimestampedRecord, table=True):
    """Persisted dataset asset and lineage reference."""

    __tablename__ = "dataset_assets"

    dataset_id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="projects.project_id", nullable=False, index=True)
    name: str = Field(index=True, min_length=1, nullable=False)
    source_type: DatasetSourceType = Field(nullable=False)
    location: str = Field(sa_column=Column(Text, nullable=False))
    version: str = Field(nullable=False, index=True)
    kind: DatasetKind = Field(nullable=False, index=True)
    role: DatasetRole = Field(default=DatasetRole.PRIMARY, nullable=False, index=True)
    parent_dataset_id: UUID | None = Field(default=None, foreign_key="dataset_assets.dataset_id")
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))


class DataProfileRecord(SQLModel, table=True):
    """Persisted dataset profile snapshot."""

    __tablename__ = "data_profiles"

    profile_id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="projects.project_id", nullable=False, index=True)
    dataset_id: UUID = Field(foreign_key="dataset_assets.dataset_id", nullable=False, index=True)
    method: DataProfileMethod = Field(nullable=False, index=True)
    schema_summary: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    baseline_summary: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    row_count: int = Field(ge=0, nullable=False)
    column_count: int = Field(ge=0, nullable=False)
    quality_flags: list[dict[str, Any]] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)


class AssumptionRecord(TimestampedRecord, table=True):
    """Persisted analytical assumption."""

    __tablename__ = "assumptions"

    assumption_id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="projects.project_id", nullable=False, index=True)
    statement: str = Field(sa_column=Column(Text, nullable=False))
    basis: str = Field(sa_column=Column(Text, nullable=False))
    confidence: ConfidenceLevel = Field(nullable=False, index=True)
    status: AssumptionStatus = Field(default=AssumptionStatus.ACTIVE, nullable=False, index=True)
    dataset_id: UUID | None = Field(default=None, foreign_key="dataset_assets.dataset_id")
    profile_id: UUID | None = Field(default=None, foreign_key="data_profiles.profile_id")
    evidence_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))


class HypothesisRecord(TimestampedRecord, table=True):
    """Persisted testable analytical hypothesis."""

    __tablename__ = "hypotheses"

    hypothesis_id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="projects.project_id", nullable=False, index=True)
    statement: str = Field(sa_column=Column(Text, nullable=False))
    variables: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    scope: str = Field(sa_column=Column(Text, nullable=False))
    validation_method: str = Field(sa_column=Column(Text, nullable=False))
    status: HypothesisStatus = Field(default=HypothesisStatus.PROPOSED, nullable=False, index=True)
    assumption_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    dataset_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    evidence_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))


class EvidenceRecord(SQLModel, table=True):
    """Persisted evidence artifact with explicit provenance fields."""

    __tablename__ = "evidence"

    evidence_id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="projects.project_id", nullable=False, index=True)
    dataset_id: UUID = Field(foreign_key="dataset_assets.dataset_id", nullable=False, index=True)
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
    limitations: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    assumption_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    hypothesis_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    decision_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)


class DecisionLogRecord(TimestampedRecord, table=True):
    """Persisted analytical decision log entry."""

    __tablename__ = "decision_logs"

    decision_id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="projects.project_id", nullable=False, index=True)
    decision_type: DecisionType = Field(nullable=False, index=True)
    decision: str = Field(sa_column=Column(Text, nullable=False))
    rationale: str = Field(sa_column=Column(Text, nullable=False))
    status: DecisionStatus = Field(default=DecisionStatus.ACTIVE, nullable=False, index=True)
    evidence_refs: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    alternatives_considered: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    assumption_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    hypothesis_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    superseded_by_decision_id: UUID | None = Field(
        default=None, foreign_key="decision_logs.decision_id"
    )


class SessionFrameRecord(SQLModel, table=True):
    """Persisted compact snapshot of active analytical context."""

    __tablename__ = "session_frames"

    session_frame_id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="projects.project_id", nullable=False, index=True)
    objective_snapshot: str = Field(sa_column=Column(Text, nullable=False))
    project_summary: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    dataset_summaries: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    active_dataset_refs: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    active_assumptions: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    active_assumption_refs: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    active_hypotheses: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    active_hypothesis_refs: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    strongest_evidence: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    strongest_evidence_refs: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    recent_decisions: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    recent_decision_refs: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    pending_tasks: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    open_questions: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    key_warnings: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)
