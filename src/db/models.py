"""SQLModel table definitions for persisted CogniEDA research state."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

from schemas.enums import (
    AssumptionSource,
    AssumptionStatus,
    AssumptionTestability,
    ConfidenceLevel,
    DataProfileLifecycleState,
    DataProfileMethod,
    DatasetSourceType,
    DiscoveryEpistemicStatus,
    EvidenceLifecycleState,
    EvidenceType,
    HypothesisStatus,
    ObjectiveStatus,
    SessionFrameStatus,
    TaskKind,
    TaskLifecycleState,
    UserDecisionStatus,
    UserDecisionType,
)


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp for persisted rows."""

    return datetime.now(UTC)


class TimestampedRecord(SQLModel):
    """Shared timestamp fields for persisted rows with lifecycle transitions."""

    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)


class ObjectiveRecord(TimestampedRecord, table=True):
    """Persisted Objective FCO for one workspace graph."""

    __tablename__ = "objectives"

    objective_id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(index=True, min_length=1, nullable=False)
    statement: str = Field(sa_column=Column(Text, nullable=False))
    status: ObjectiveStatus = Field(default=ObjectiveStatus.ACTIVE, nullable=False, index=True)


class DataProfileRecord(SQLModel, table=True):
    """Persisted immutable DataProfile snapshot."""

    __tablename__ = "data_profiles"

    profile_id: UUID = Field(default_factory=uuid4, primary_key=True)
    dataset_path: str = Field(sa_column=Column(Text, nullable=False))
    source_type: DatasetSourceType = Field(default=DatasetSourceType.FILE, nullable=False)
    dvc_hash: str | None = Field(default=None, index=True)
    dvc_version_label: str | None = Field(default=None, index=True)
    source_uri: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    source_description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
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
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    preprocessing_history: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    artifact_refs: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    lifecycle_state: DataProfileLifecycleState = Field(
        default=DataProfileLifecycleState.DRAFT,
        nullable=False,
        index=True,
    )
    accepted_as_ground_truth: bool = Field(default=False, nullable=False, index=True)
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)


class AssumptionRecord(TimestampedRecord, table=True):
    """Persisted Assumption FCO."""

    __tablename__ = "assumptions"

    assumption_id: UUID = Field(default_factory=uuid4, primary_key=True)
    statement: str = Field(sa_column=Column(Text, nullable=False))
    scope: str = Field(sa_column=Column(Text, nullable=False))
    source: AssumptionSource = Field(default=AssumptionSource.USER, nullable=False, index=True)
    testability: AssumptionTestability = Field(
        default=AssumptionTestability.UNTESTABLE_IN_PROJECT,
        nullable=False,
        index=True,
    )
    basis: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    confidence: ConfidenceLevel = Field(default=ConfidenceLevel.MEDIUM, nullable=False, index=True)
    status: AssumptionStatus = Field(default=AssumptionStatus.ACTIVE, nullable=False, index=True)
    scoped_data_profile_ids: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    contradicted_by_discovery_ids: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    replacement_assumption_id: UUID | None = Field(
        default=None,
        foreign_key="assumptions.assumption_id",
    )


class TaskRecord(TimestampedRecord, table=True):
    """Persisted Task FCO."""

    __tablename__ = "tasks"

    task_id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(sa_column=Column(Text, nullable=False))
    description: str = Field(sa_column=Column(Text, nullable=False))
    lifecycle_state: TaskLifecycleState = Field(
        default=TaskLifecycleState.ACTIVE,
        nullable=False,
        index=True,
    )
    task_kind: TaskKind = Field(default=TaskKind.ANALYTICAL, nullable=False, index=True)
    parent_task_id: UUID | None = Field(default=None, foreign_key="tasks.task_id", index=True)
    profile_id: UUID | None = Field(default=None, foreign_key="data_profiles.profile_id")
    variables: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    evidence_expectation: str | None = Field(default=None, sa_column=Column(Text, nullable=True))


class HypothesisRecord(TimestampedRecord, table=True):
    """Persisted Hypothesis FCO."""

    __tablename__ = "hypotheses"
    __table_args__ = (UniqueConstraint("task_id", name="uq_hypotheses_task_id"),)

    hypothesis_id: UUID = Field(default_factory=uuid4, primary_key=True)
    task_id: UUID = Field(foreign_key="tasks.task_id", nullable=False, index=True)
    profile_id: UUID = Field(foreign_key="data_profiles.profile_id", nullable=False, index=True)
    statement: str = Field(sa_column=Column(Text, nullable=False))
    variables: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    scope: str = Field(sa_column=Column(Text, nullable=False))
    validation_method: str = Field(sa_column=Column(Text, nullable=False))
    evidence_expectation: str = Field(sa_column=Column(Text, nullable=False))
    status: HypothesisStatus = Field(default=HypothesisStatus.PROPOSED, nullable=False, index=True)


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
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)


class DiscoveryRecord(SQLModel, table=True):
    """Persisted immutable Discovery FCO."""

    __tablename__ = "discoveries"
    __table_args__ = (UniqueConstraint("hypothesis_id", name="uq_discoveries_hypothesis_id"),)

    discovery_id: UUID = Field(default_factory=uuid4, primary_key=True)
    hypothesis_id: UUID = Field(foreign_key="hypotheses.hypothesis_id", nullable=False, index=True)
    evidence_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    claim: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    epistemic_status: DiscoveryEpistemicStatus = Field(nullable=False, index=True)
    scope: str = Field(sa_column=Column(Text, nullable=False))
    validity_basis: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)


class UserDecisionRecord(TimestampedRecord, table=True):
    """Typed provenance for a user decision."""

    __tablename__ = "user_decisions"

    decision_id: UUID = Field(default_factory=uuid4, primary_key=True)
    decision_type: UserDecisionType = Field(nullable=False, index=True)
    decision: str = Field(sa_column=Column(Text, nullable=False))
    rationale: str = Field(sa_column=Column(Text, nullable=False))
    status: UserDecisionStatus = Field(
        default=UserDecisionStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    alternatives_considered: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    related_task_ids: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    related_hypothesis_ids: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    superseded_by_decision_id: UUID | None = Field(
        default=None,
        foreign_key="user_decisions.decision_id",
    )


class SessionFrameRecord(SQLModel, table=True):
    """Persisted concrete active-context frame."""

    __tablename__ = "session_frames"

    session_frame_id: UUID = Field(default_factory=uuid4, primary_key=True)
    frame_topic: str = Field(sa_column=Column(Text, nullable=False))
    frame_status: SessionFrameStatus = Field(
        default=SessionFrameStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    objective_snapshot: str = Field(sa_column=Column(Text, nullable=False))
    frame_outcome: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    objective_summary: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    branch_key: str | None = Field(default=None, index=True)
    checkpoint_label: str | None = Field(default=None, index=True)
    parent_session_frame_id: UUID | None = Field(
        default=None,
        foreign_key="session_frames.session_frame_id",
    )
    handoff_summary: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    data_profile_summaries: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    active_data_profile_refs: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    active_tasks: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    active_task_refs: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    active_assumptions: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    active_assumption_refs: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    active_hypotheses: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    active_hypothesis_refs: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    relevant_discoveries: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    relevant_discovery_refs: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    supporting_evidence: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    supporting_evidence_refs: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    recent_user_decisions: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    recent_user_decision_refs: list[str] = Field(
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
