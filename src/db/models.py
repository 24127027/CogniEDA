"""SQLModel table definitions for persisted CogniEDA artifacts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, Text, UniqueConstraint
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
    HypothesisEvidenceOutcome,
    HypothesisStatus,
    ProjectStatus,
    SessionFrameStatus,
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
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "name",
            "version",
            name="uq_dataset_assets_project_name_version",
        ),
    )

    dataset_id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="projects.project_id", nullable=False, index=True)
    name: str = Field(index=True, min_length=1, nullable=False)
    source_type: DatasetSourceType = Field(nullable=False)
    location: str = Field(sa_column=Column(Text, nullable=False))
    version: str = Field(nullable=False, index=True)
    kind: DatasetKind = Field(nullable=False, index=True)
    role: DatasetRole = Field(default=DatasetRole.PRIMARY, nullable=False, index=True)
    lineage_steps: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))


class DatasetLineageLinkRecord(SQLModel, table=True):
    """Normalized upstream lineage links for a dataset asset."""

    __tablename__ = "dataset_lineage_links"

    dataset_id: UUID = Field(foreign_key="dataset_assets.dataset_id", primary_key=True)
    upstream_dataset_id: UUID = Field(foreign_key="dataset_assets.dataset_id", primary_key=True)


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


class HypothesisAssumptionLinkRecord(SQLModel, table=True):
    """Normalized assumption links for a hypothesis."""

    __tablename__ = "hypothesis_assumption_links"

    hypothesis_id: UUID = Field(foreign_key="hypotheses.hypothesis_id", primary_key=True)
    assumption_id: UUID = Field(foreign_key="assumptions.assumption_id", primary_key=True)


class HypothesisDatasetLinkRecord(SQLModel, table=True):
    """Normalized dataset links for a hypothesis."""

    __tablename__ = "hypothesis_dataset_links"

    hypothesis_id: UUID = Field(foreign_key="hypotheses.hypothesis_id", primary_key=True)
    dataset_id: UUID = Field(foreign_key="dataset_assets.dataset_id", primary_key=True)


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
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)


class EvidenceAssumptionLinkRecord(SQLModel, table=True):
    """Normalized assumption links for an evidence artifact."""

    __tablename__ = "evidence_assumption_links"

    evidence_id: UUID = Field(foreign_key="evidence.evidence_id", primary_key=True)
    assumption_id: UUID = Field(foreign_key="assumptions.assumption_id", primary_key=True)


class EvidenceHypothesisLinkRecord(SQLModel, table=True):
    """Normalized evaluated-hypothesis links for an evidence artifact."""

    __tablename__ = "evidence_hypothesis_links"

    evidence_id: UUID = Field(foreign_key="evidence.evidence_id", primary_key=True)
    hypothesis_id: UUID = Field(foreign_key="hypotheses.hypothesis_id", primary_key=True)
    outcome: HypothesisEvidenceOutcome = Field(nullable=False, index=True)
    note: str | None = Field(default=None, sa_column=Column(Text, nullable=True))


class EvidenceDecisionLinkRecord(SQLModel, table=True):
    """Normalized decision links for an evidence artifact."""

    __tablename__ = "evidence_decision_links"

    evidence_id: UUID = Field(foreign_key="evidence.evidence_id", primary_key=True)
    decision_id: UUID = Field(foreign_key="decision_logs.decision_id", primary_key=True)


class DecisionLogRecord(TimestampedRecord, table=True):
    """Persisted analytical decision log entry."""

    __tablename__ = "decision_logs"

    decision_id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="projects.project_id", nullable=False, index=True)
    decision_type: DecisionType = Field(nullable=False, index=True)
    decision: str = Field(sa_column=Column(Text, nullable=False))
    rationale: str = Field(sa_column=Column(Text, nullable=False))
    status: DecisionStatus = Field(default=DecisionStatus.ACTIVE, nullable=False, index=True)
    alternatives_considered: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    superseded_by_decision_id: UUID | None = Field(
        default=None, foreign_key="decision_logs.decision_id"
    )


class DecisionAssumptionLinkRecord(SQLModel, table=True):
    """Normalized assumption links for a decision log artifact."""

    __tablename__ = "decision_assumption_links"

    decision_id: UUID = Field(foreign_key="decision_logs.decision_id", primary_key=True)
    assumption_id: UUID = Field(foreign_key="assumptions.assumption_id", primary_key=True)


class DecisionHypothesisLinkRecord(SQLModel, table=True):
    """Normalized hypothesis links for a decision log artifact."""

    __tablename__ = "decision_hypothesis_links"

    decision_id: UUID = Field(foreign_key="decision_logs.decision_id", primary_key=True)
    hypothesis_id: UUID = Field(foreign_key="hypotheses.hypothesis_id", primary_key=True)


class SessionFrameRecord(SQLModel, table=True):
    """Persisted concrete context frame snapshot for analytical continuity."""

    __tablename__ = "session_frames"

    session_frame_id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="projects.project_id", nullable=False, index=True)
    frame_topic: str = Field(sa_column=Column(Text, nullable=False))
    frame_status: SessionFrameStatus = Field(
        default=SessionFrameStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    objective_snapshot: str = Field(sa_column=Column(Text, nullable=False))
    frame_outcome: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    project_summary: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    branch_key: str | None = Field(default=None, index=True)
    checkpoint_label: str | None = Field(default=None, index=True)
    parent_session_frame_id: UUID | None = Field(
        default=None,
        foreign_key="session_frames.session_frame_id",
    )
    handoff_summary: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
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
    stale_context: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    dead_ends: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    cached_tool_results: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    frame_invalidation_rules: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)
