"""Core research-state models for CogniEDA."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import Field, NonNegativeInt, model_validator

from schemas.common import (
    AssumptionContextSummary,
    CogniEDABaseModel,
    ColumnProfile,
    DataProfileContextSummary,
    DeadEndSummary,
    DiscoveryClaim,
    DiscoveryContextSummary,
    EvidenceContextSummary,
    EvidenceProvenance,
    EvidenceResultSummary,
    HypothesisContextSummary,
    ImmutableCogniEDABaseModel,
    InvalidationRule,
    MethodParameter,
    NonEmptyStr,
    StaleContextMarker,
    TaskContextSummary,
    ToolResultCacheSummary,
    UserDecisionContextSummary,
    ValidityBasis,
    utc_now,
)
from schemas.enums import (
    DiscoveryEpistemicStatus,
    DiscoveryLifecycleState,
    EvidenceLifecycleState,
    EvidenceType,
    HypothesisStatus,
    SessionFrameStatus,
    TaskStatus,
    UserDecisionStatus,
    UserDecisionType,
)


class Objective(CogniEDABaseModel):
    """Minimum executable research intent for the active MVP session."""

    objective_id: UUID = Field(default_factory=uuid4)
    text: NonEmptyStr


class DataProfile(ImmutableCogniEDABaseModel):
    """Immutable typed description of the single active MVP dataset."""

    data_profile_id: UUID = Field(default_factory=uuid4)
    row_count: NonNegativeInt
    column_count: NonNegativeInt
    columns: tuple[ColumnProfile, ...]

    @model_validator(mode="after")
    def _column_count_matches_columns(self) -> DataProfile:
        if self.column_count != len(self.columns):
            raise ValueError("column_count must equal the number of ColumnProfile entries.")
        return self


class Assumption(CogniEDABaseModel):
    """Planning-only statement; an Assumption is never empirical Evidence."""

    assumption_id: UUID = Field(default_factory=uuid4)
    text: NonEmptyStr


class Task(CogniEDABaseModel):
    """Bounded executable MVP work identity; a Task is not scientific knowledge."""

    task_id: UUID = Field(default_factory=uuid4)
    instruction: NonEmptyStr
    status: TaskStatus = TaskStatus.PENDING


class Hypothesis(CogniEDABaseModel):
    """Atomic test contract created from one terminal analytical Task."""

    hypothesis_id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    profile_id: UUID
    statement: NonEmptyStr
    variables: list[NonEmptyStr] = Field(default_factory=list)
    scope: NonEmptyStr
    validation_method: NonEmptyStr
    evidence_expectation: NonEmptyStr
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Evidence(ImmutableCogniEDABaseModel):
    """Directly observed analytical result, not interpretation."""

    evidence_id: UUID = Field(default_factory=uuid4)
    hypothesis_id: UUID
    profile_id: UUID
    # Skeleton stage: these are string identifiers for provenance records.
    # EvidenceRepository can strictly dereference them when provenance repos are wired.
    analysis_frame_ref: NonEmptyStr
    execution_run_ref: NonEmptyStr
    evidence_type: EvidenceType
    method: NonEmptyStr
    parameters: list[MethodParameter] = Field(default_factory=list)
    provenance: EvidenceProvenance
    result_summary: EvidenceResultSummary
    artifact_refs: list[NonEmptyStr] = Field(default_factory=list)
    limitations: list[NonEmptyStr] = Field(default_factory=list)
    lifecycle_state: EvidenceLifecycleState = EvidenceLifecycleState.ACTIVE
    superseded_by_evidence_id: UUID | None = None
    lifecycle_reason: str | None = None
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _provenance_matches_required_refs(self) -> Evidence:
        if self.provenance.analysis_frame_ref != self.analysis_frame_ref:
            raise ValueError("Evidence provenance must reference the same AnalysisFrame.")
        if self.provenance.execution_run_ref != self.execution_run_ref:
            raise ValueError("Evidence provenance must reference the same ExecutionRun.")
        return self


class Discovery(ImmutableCogniEDABaseModel):
    """Evidence-bound claim produced from exactly one Hypothesis."""

    discovery_id: UUID = Field(default_factory=uuid4)
    hypothesis_id: UUID
    evidence_ids: list[UUID]
    claim: DiscoveryClaim
    epistemic_status: DiscoveryEpistemicStatus
    scope: NonEmptyStr
    validity_basis: ValidityBasis
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


class UserDecision(CogniEDABaseModel):
    """Typed provenance record for a user decision."""

    decision_id: UUID = Field(default_factory=uuid4)
    decision_type: UserDecisionType
    decision: NonEmptyStr
    rationale: NonEmptyStr
    status: UserDecisionStatus = UserDecisionStatus.ACTIVE
    alternatives_considered: list[NonEmptyStr] = Field(default_factory=list)
    related_task_ids: list[UUID] = Field(default_factory=list)
    related_hypothesis_ids: list[UUID] = Field(default_factory=list)
    superseded_by_decision_id: UUID | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class SessionFrame(CogniEDABaseModel):
    """Concrete active-context frame for session continuity and handoff."""

    session_frame_id: UUID = Field(default_factory=uuid4)
    frame_topic: NonEmptyStr
    frame_status: SessionFrameStatus = SessionFrameStatus.ACTIVE
    objective_snapshot: NonEmptyStr
    frame_outcome: str | None = None
    objective_summary: str | None = None
    branch_key: str | None = None
    checkpoint_label: str | None = None
    parent_session_frame_id: UUID | None = None
    handoff_summary: str | None = None
    data_profile_summaries: list[DataProfileContextSummary] = Field(default_factory=list)
    active_data_profile_refs: list[UUID] = Field(default_factory=list)
    active_tasks: list[TaskContextSummary] = Field(default_factory=list)
    active_task_refs: list[UUID] = Field(default_factory=list)
    active_assumptions: list[AssumptionContextSummary] = Field(default_factory=list)
    active_assumption_refs: list[UUID] = Field(default_factory=list)
    active_hypotheses: list[HypothesisContextSummary] = Field(default_factory=list)
    active_hypothesis_refs: list[UUID] = Field(default_factory=list)
    relevant_discoveries: list[DiscoveryContextSummary] = Field(default_factory=list)
    relevant_discovery_refs: list[UUID] = Field(default_factory=list)
    supporting_evidence: list[EvidenceContextSummary] = Field(default_factory=list)
    supporting_evidence_refs: list[UUID] = Field(default_factory=list)
    recent_user_decisions: list[UserDecisionContextSummary] = Field(default_factory=list)
    recent_user_decision_refs: list[UUID] = Field(default_factory=list)
    pending_tasks: list[NonEmptyStr] = Field(default_factory=list)
    open_questions: list[NonEmptyStr] = Field(default_factory=list)
    key_warnings: list[NonEmptyStr] = Field(default_factory=list)
    stale_context: list[StaleContextMarker] = Field(default_factory=list)
    dead_ends: list[DeadEndSummary] = Field(default_factory=list)
    cached_tool_results: list[ToolResultCacheSummary] = Field(default_factory=list)
    frame_invalidation_rules: list[InvalidationRule] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
