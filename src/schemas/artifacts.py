"""Core analytical artifact models for CogniEDA."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import Field, NonNegativeInt
from schemas.common import (
    AssumptionContextSummary,
    BaselineSummary,
    CogniEDABaseModel,
    DatasetContextSummary,
    DeadEndSummary,
    DecisionContextSummary,
    EvidenceContextSummary,
    EvidenceProvenance,
    EvidenceResultSummary,
    HypothesisContextSummary,
    HypothesisEvaluation,
    InvalidationRule,
    LineageStep,
    MethodParameter,
    NonEmptyStr,
    QualityFlag,
    SchemaSummary,
    StaleContextMarker,
    ToolResultCacheSummary,
    utc_now,
)
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
    SessionFrameStatus,
)


class Project(CogniEDABaseModel):
    """Root analytical container for an investigation and its durable context."""

    project_id: UUID = Field(default_factory=uuid4)
    name: NonEmptyStr
    objective: NonEmptyStr
    research_questions: list[NonEmptyStr] = Field(default_factory=list)
    status: ProjectStatus = ProjectStatus.ACTIVE
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class DatasetAsset(CogniEDABaseModel):
    """Versioned reference to a raw or derived dataset used in analysis."""

    dataset_id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    name: NonEmptyStr
    source_type: DatasetSourceType
    location: NonEmptyStr
    version: NonEmptyStr
    kind: DatasetKind
    role: DatasetRole = DatasetRole.PRIMARY
    upstream_dataset_ids: list[UUID] = Field(default_factory=list)
    lineage_steps: list[LineageStep] = Field(default_factory=list)
    description: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class DataProfile(CogniEDABaseModel):
    """Reproducible structural and baseline summary for a dataset version."""

    profile_id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    dataset_id: UUID
    method: DataProfileMethod
    schema_summary: SchemaSummary
    baseline_summary: BaselineSummary
    row_count: NonNegativeInt
    column_count: NonNegativeInt
    quality_flags: list[QualityFlag] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class Assumption(CogniEDABaseModel):
    """Provisional analytical statement used to guide investigation."""

    assumption_id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    statement: NonEmptyStr
    basis: NonEmptyStr
    confidence: ConfidenceLevel
    status: AssumptionStatus = AssumptionStatus.ACTIVE
    dataset_id: UUID | None = None
    profile_id: UUID | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Hypothesis(CogniEDABaseModel):
    """Testable analytical claim with explicit validation state."""

    hypothesis_id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    statement: NonEmptyStr
    variables: list[NonEmptyStr] = Field(default_factory=list)
    scope: NonEmptyStr
    validation_method: NonEmptyStr
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    assumption_ids: list[UUID] = Field(default_factory=list)
    dataset_ids: list[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Evidence(CogniEDABaseModel):
    """Reproducible analytical result with explicit provenance fields."""

    evidence_id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    dataset_id: UUID
    evidence_type: EvidenceType
    method: NonEmptyStr
    parameters: list[MethodParameter] = Field(default_factory=list)
    provenance: EvidenceProvenance
    result_summary: EvidenceResultSummary
    limitations: list[NonEmptyStr] = Field(default_factory=list)
    assumption_ids: list[UUID] = Field(default_factory=list)
    hypothesis_evaluations: list[HypothesisEvaluation] = Field(default_factory=list)
    decision_ids: list[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class DecisionLog(CogniEDABaseModel):
    """Record of a meaningful analytical choice and its supporting rationale."""

    decision_id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    decision_type: DecisionType
    decision: NonEmptyStr
    rationale: NonEmptyStr
    status: DecisionStatus = DecisionStatus.ACTIVE
    alternatives_considered: list[NonEmptyStr] = Field(default_factory=list)
    assumption_ids: list[UUID] = Field(default_factory=list)
    hypothesis_ids: list[UUID] = Field(default_factory=list)
    superseded_by_decision_id: UUID | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class SessionFrame(CogniEDABaseModel):
    """Concrete persisted context frame for session continuity and handoff."""

    session_frame_id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    frame_topic: NonEmptyStr
    frame_status: SessionFrameStatus = SessionFrameStatus.ACTIVE
    objective_snapshot: NonEmptyStr
    frame_outcome: str | None = None
    project_summary: str | None = None
    branch_key: str | None = None
    checkpoint_label: str | None = None
    parent_session_frame_id: UUID | None = None
    handoff_summary: str | None = None
    dataset_summaries: list[DatasetContextSummary] = Field(default_factory=list)
    active_dataset_refs: list[UUID] = Field(default_factory=list)
    active_assumptions: list[AssumptionContextSummary] = Field(default_factory=list)
    active_assumption_refs: list[UUID] = Field(default_factory=list)
    active_hypotheses: list[HypothesisContextSummary] = Field(default_factory=list)
    active_hypothesis_refs: list[UUID] = Field(default_factory=list)
    strongest_evidence: list[EvidenceContextSummary] = Field(default_factory=list)
    strongest_evidence_refs: list[UUID] = Field(default_factory=list)
    recent_decisions: list[DecisionContextSummary] = Field(default_factory=list)
    recent_decision_refs: list[UUID] = Field(default_factory=list)
    pending_tasks: list[NonEmptyStr] = Field(default_factory=list)
    open_questions: list[NonEmptyStr] = Field(default_factory=list)
    key_warnings: list[NonEmptyStr] = Field(default_factory=list)
    stale_context: list[StaleContextMarker] = Field(default_factory=list)
    dead_ends: list[DeadEndSummary] = Field(default_factory=list)
    cached_tool_results: list[ToolResultCacheSummary] = Field(default_factory=list)
    frame_invalidation_rules: list[InvalidationRule] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
