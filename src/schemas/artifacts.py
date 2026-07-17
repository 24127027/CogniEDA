"""Core research-state models for CogniEDA."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import Field, NonNegativeInt, model_validator

from schemas.common import (
    AssumptionContextSummary,
    BaselineSummary,
    CogniEDABaseModel,
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
    LineageStep,
    MethodParameter,
    NonEmptyStr,
    QualityFlag,
    SchemaSummary,
    StaleContextMarker,
    TaskContextSummary,
    ToolResultCacheSummary,
    UserDecisionContextSummary,
    ValidityBasis,
    utc_now,
)
from schemas.enums import (
    AssumptionSource,
    AssumptionStatus,
    AssumptionTestability,
    ConfidenceLevel,
    DataProfileLifecycleState,
    DataProfileMethod,
    DatasetSourceType,
    DiscoveryEpistemicStatus,
    DiscoveryLifecycleState,
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


class Objective(CogniEDABaseModel):
    """Research intent for one workspace graph."""

    objective_id: UUID = Field(default_factory=uuid4)
    title: NonEmptyStr
    statement: NonEmptyStr
    status: ObjectiveStatus = ObjectiveStatus.ACTIVE
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class DataProfile(ImmutableCogniEDABaseModel):
    """Immutable semantic profile for one dataset version."""

    profile_id: UUID = Field(default_factory=uuid4)
    dataset_path: NonEmptyStr
    source_type: DatasetSourceType = DatasetSourceType.FILE
    dvc_hash: str | None = None
    dvc_version_label: str | None = None
    source_uri: str | None = None
    source_description: str | None = None
    method: DataProfileMethod
    schema_summary: SchemaSummary
    baseline_summary: BaselineSummary
    row_count: NonNegativeInt
    column_count: NonNegativeInt
    quality_flags: list[QualityFlag] = Field(default_factory=list)
    preprocessing_history: list[LineageStep] = Field(default_factory=list)
    artifact_refs: list[NonEmptyStr] = Field(default_factory=list)
    lifecycle_state: DataProfileLifecycleState = DataProfileLifecycleState.DRAFT
    superseded_by_data_profile_id: UUID | None = None
    accepted_as_ground_truth: bool = False
    created_at: datetime = Field(default_factory=utc_now)


class Assumption(CogniEDABaseModel):
    """Provisional analytical statement used for planning, not inference."""

    assumption_id: UUID = Field(default_factory=uuid4)
    statement: NonEmptyStr
    scope: NonEmptyStr
    source: AssumptionSource = AssumptionSource.USER
    testability: AssumptionTestability = AssumptionTestability.UNTESTABLE_IN_PROJECT
    basis: NonEmptyStr | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    status: AssumptionStatus = AssumptionStatus.ACTIVE
    scoped_data_profile_ids: list[UUID] = Field(default_factory=list)
    contradicted_by_discovery_ids: list[UUID] = Field(default_factory=list)
    replacement_assumption_id: UUID | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _reject_testable_claim_as_assumption(self) -> Assumption:
        if (
            self.testability
            == AssumptionTestability.TESTABLE_CLAIM_REJECTED_AS_ASSUMPTION
        ):
            raise ValueError(
                "Testable claims must become Task/Hypothesis candidates, not Assumptions."
            )
        return self


class Task(CogniEDABaseModel):
    """Durable workflow state. A Task is not scientific knowledge."""

    task_id: UUID = Field(default_factory=uuid4)
    title: NonEmptyStr
    description: NonEmptyStr
    lifecycle_state: TaskLifecycleState = TaskLifecycleState.ACTIVE
    task_kind: TaskKind = TaskKind.ANALYTICAL
    parent_task_id: UUID | None = None
    profile_id: UUID | None = None
    variables: list[NonEmptyStr] = Field(default_factory=list)
    evidence_expectation: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def can_generate_hypothesis(
        self,
        *,
        has_child_tasks: bool = False,
        data_profile_accepted: bool = True,
    ) -> bool:
        """Return whether this Task satisfies local hypothesis-admission guards."""

        return (
            self.lifecycle_state == TaskLifecycleState.ACTIVE
            and self.task_kind == TaskKind.ANALYTICAL
            and not has_child_tasks
            and data_profile_accepted
            and self.profile_id is not None
            and len(self.variables) > 0
            and bool(self.evidence_expectation)
        )


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
