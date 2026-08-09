"""Shared value objects and helpers for CogniEDA schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from math import isfinite
from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeFloat,
    NonNegativeInt,
    field_validator,
    model_validator,
)

from schemas.enums import (
    ConfidenceLevel,
    DataProfileLifecycleState,
    DiscoveryEpistemicStatus,
    DiscoveryLifecycleState,
    EvidenceLifecycleState,
    EvidenceType,
    HypothesisEvidenceOutcome,
    HypothesisStatus,
    InvalidationTrigger,
    LineageOperationType,
    LogicalDtype,
    MemorySourceType,
    MemoryStatus,
    QualityFlagSeverity,
    UserDecisionStatus,
    UserDecisionType,
    VariableType,
)

type NonEmptyStr = Annotated[str, Field(min_length=1)]
type ScalarParameterValue = str | int | float | bool | None


_UNQUALIFIED_ABSENCE_PHRASES = (
    "there is no relationship",
    "there is no association",
    "no relationship exists",
    "no association exists",
)

_INSUFFICIENT_EVIDENCE_QUALIFIERS = (
    "insufficient",
    "not sufficient",
    "fail to reject",
    "failed to reject",
)


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(UTC)


def reject_unqualified_absence_claim(value: str) -> str:
    """Reject over-strong absence wording for inconclusive analytical results."""

    normalized = value.lower()
    has_absence_phrase = any(phrase in normalized for phrase in _UNQUALIFIED_ABSENCE_PHRASES)
    has_qualifier = any(qualifier in normalized for qualifier in _INSUFFICIENT_EVIDENCE_QUALIFIERS)
    if has_absence_phrase and not has_qualifier:
        raise ValueError(
            "Use scoped insufficient-evidence wording instead of an unqualified "
            "'no relationship' claim."
        )
    return value


class CogniEDABaseModel(BaseModel):
    """Shared base model for all CogniEDA schema objects."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_assignment=True)


class ImmutableCogniEDABaseModel(CogniEDABaseModel):
    """Base model for append-only research records."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class MethodParameter(CogniEDABaseModel):
    """Typed method parameter entry used instead of ad hoc dictionaries."""

    name: NonEmptyStr
    value: ScalarParameterValue


class LineageStep(CogniEDABaseModel):
    """Explicit transformation step recorded in profile preprocessing history."""

    operation_type: LineageOperationType
    description: NonEmptyStr
    input_profile_ids: list[UUID] = Field(default_factory=list)
    column_names: list[NonEmptyStr] = Field(default_factory=list)
    row_constraint: str | None = None
    parameters: list[MethodParameter] = Field(default_factory=list)
    code_reference: str | None = None


class TopValueSummary(CogniEDABaseModel):
    """Frequency summary for a categorical top value."""

    value: NonEmptyStr
    count: NonNegativeInt
    ratio: NonNegativeFloat = Field(ge=0.0, le=1.0)


class NumericColumnSummary(CogniEDABaseModel):
    """Deterministic baseline statistics for a numeric column."""

    count: NonNegativeInt
    mean: float | None = None
    std: float | None = None
    min_value: float | None = None
    percentile_25: float | None = None
    median: float | None = None
    percentile_75: float | None = None
    max_value: float | None = None


class CategoricalColumnSummary(CogniEDABaseModel):
    """Cardinality and top-value summary for a categorical-like column."""

    unique_count: NonNegativeInt
    top_values: list[TopValueSummary] = Field(default_factory=list)


class ColumnSchemaSummary(CogniEDABaseModel):
    """Schema-level summary for one inferred dataset column."""

    name: NonEmptyStr
    inferred_dtype: NonEmptyStr
    logical_dtype: LogicalDtype
    observed_nullable: bool
    non_null_count: NonNegativeInt = 0
    distinct_count: NonNegativeInt | None = None
    missing_count: NonNegativeInt = 0
    missing_ratio: NonNegativeFloat = Field(default=0.0, le=1.0)
    numeric_summary: NumericColumnSummary | None = None
    categorical_summary: CategoricalColumnSummary | None = None


class SchemaSummary(CogniEDABaseModel):
    """Structural schema summary inferred from a dataset version."""

    columns: list[ColumnSchemaSummary] = Field(default_factory=list)
    column_order: list[NonEmptyStr] = Field(default_factory=list)
    detected_primary_key: str | None = None
    inferred_time_columns: list[NonEmptyStr] = Field(default_factory=list)


class BaselineSummary(CogniEDABaseModel):
    """Baseline row-level quality summary for a profiled dataset."""

    column_names: list[NonEmptyStr] = Field(default_factory=list)
    missing_cell_count: NonNegativeInt = 0
    missing_cell_ratio: NonNegativeFloat = Field(default=0.0, le=1.0)
    duplicate_row_count: NonNegativeInt = 0
    duplicate_row_ratio: NonNegativeFloat = Field(default=0.0, le=1.0)
    numeric_column_count: NonNegativeInt = 0
    categorical_column_count: NonNegativeInt = 0
    columns_with_missing_values: list[NonEmptyStr] = Field(default_factory=list)
    warning_codes: list[NonEmptyStr] = Field(default_factory=list)


class QualityFlag(CogniEDABaseModel):
    """Typed quality flag emitted during data profiling."""

    code: NonEmptyStr
    severity: QualityFlagSeverity
    message: NonEmptyStr
    column_name: str | None = None


class ContinuousColumnSummary(ImmutableCogniEDABaseModel):
    """Finite descriptive statistics for one continuous MVP column."""

    min: float | None = None
    max: float | None = None
    mean: float | None = None
    median: float | None = None
    std: float | None = None
    p25: float | None = None
    p75: float | None = None

    @field_validator("min", "max", "mean", "median", "std", "p25", "p75")
    @classmethod
    def _statistics_must_be_finite(cls, value: float | None) -> float | None:
        if value is not None and not isfinite(value):
            raise ValueError("Continuous summary statistics must be finite.")
        return value


class DiscreteValueCount(ImmutableCogniEDABaseModel):
    """JSON-safe value and frequency pair for one discrete column."""

    value: str | int | float | bool
    count: NonNegativeInt


class DiscreteColumnSummary(ImmutableCogniEDABaseModel):
    """Complete low-cardinality counts or bounded high-cardinality top values."""

    value_counts: tuple[DiscreteValueCount, ...] | None = None
    top_values: tuple[DiscreteValueCount, ...] | None = None

    @field_validator("top_values")
    @classmethod
    def _top_values_must_be_bounded(
        cls, value: tuple[DiscreteValueCount, ...] | None
    ) -> tuple[DiscreteValueCount, ...] | None:
        if value is not None and not value:
            raise ValueError("top_values must contain at least one value when present.")
        return value

    @model_validator(mode="after")
    def _has_exactly_one_count_representation(self) -> DiscreteColumnSummary:
        if (self.value_counts is None) == (self.top_values is None):
            raise ValueError("Provide exactly one of value_counts or top_values.")
        return self


class ColumnProfile(ImmutableCogniEDABaseModel):
    """Typed deterministic profile for one dataset column."""

    name: NonEmptyStr
    dtype: NonEmptyStr
    variable_type: VariableType
    distinct_count: NonNegativeInt
    missing_count: NonNegativeInt
    summary: ContinuousColumnSummary | DiscreteColumnSummary

    @model_validator(mode="after")
    def _summary_matches_variable_type(self) -> ColumnProfile:
        if self.variable_type is VariableType.CONTINUOUS and not isinstance(
            self.summary, ContinuousColumnSummary
        ):
            raise ValueError("CONTINUOUS columns require ContinuousColumnSummary.")
        if self.variable_type is VariableType.DISCRETE and not isinstance(
            self.summary, DiscreteColumnSummary
        ):
            raise ValueError("DISCRETE columns require DiscreteColumnSummary.")
        return self


class EvidenceProvenance(ImmutableCogniEDABaseModel):
    """Bounded MVP lineage from Evidence to dataset/tool work."""

    producer_role: NonEmptyStr
    work_reference: NonEmptyStr
    dataset_reference: NonEmptyStr
    data_profile_id: UUID
    tool_reference: NonEmptyStr | None = None
    code_reference: NonEmptyStr | None = None


class HypothesisEvaluation(CogniEDABaseModel):
    """Typed observed outcome for one hypothesis."""

    hypothesis_id: UUID
    outcome: HypothesisEvidenceOutcome
    note: str | None = None


class EvidenceResultSummary(CogniEDABaseModel):
    """Compact, typed result payload for an Evidence record."""

    summary: NonEmptyStr
    key_findings: list[NonEmptyStr] = Field(default_factory=list)
    metric_name: str | None = None
    metric_value: ScalarParameterValue = None
    metric_unit: str | None = None

    @field_validator("summary")
    @classmethod
    def _summary_avoids_unqualified_absence_claim(cls, value: str) -> str:
        return reject_unqualified_absence_claim(value)

    @field_validator("key_findings")
    @classmethod
    def _findings_avoid_unqualified_absence_claim(cls, values: list[str]) -> list[str]:
        return [reject_unqualified_absence_claim(value) for value in values]


class DiscoveryClaim(CogniEDABaseModel):
    """Structured evidence-bound claim content."""

    statement: NonEmptyStr
    scope: NonEmptyStr
    conditions: list[NonEmptyStr] = Field(default_factory=list)
    result: str | None = None

    @field_validator("statement")
    @classmethod
    def _statement_avoids_unqualified_absence_claim(cls, value: str) -> str:
        return reject_unqualified_absence_claim(value)


class ValidityBasis(CogniEDABaseModel):
    """Dependency and invalidation contract for a Discovery claim."""

    data_profile_id: UUID
    analysis_frame_refs: list[NonEmptyStr]
    hypothesis_id: UUID
    evidence_ids: list[UUID]
    method: NonEmptyStr
    parameters: list[MethodParameter] = Field(default_factory=list)
    code_reference: str | None = None
    environment_reference: str | None = None
    decision_rule: NonEmptyStr
    strength: str | None = None
    uncertainty: str | None = None
    assumptions_excluded_from_inference: bool = True
    invalidators: list[NonEmptyStr] = Field(default_factory=list)


class ContextProvenance(CogniEDABaseModel):
    """Typed provenance entry for one context-frame item."""

    source_type: MemorySourceType
    reference: str | None = None
    note: str | None = None


class InvalidationRule(CogniEDABaseModel):
    """Explicit invalidation rule for cached or summarized context."""

    trigger: InvalidationTrigger
    detail: str | None = None


class StaleContextMarker(CogniEDABaseModel):
    """Marker describing context that should not continue influencing reasoning."""

    artifact_type: NonEmptyStr
    reason: NonEmptyStr
    ref_id: UUID | None = None
    replacement_ref_id: UUID | None = None


class DeadEndSummary(CogniEDABaseModel):
    """Recorded analytical path that should not be retried without new conditions."""

    summary: NonEmptyStr
    reason: NonEmptyStr
    related_profile_id: UUID | None = None
    related_hypothesis_id: UUID | None = None
    revived_only_if: str | None = None


class ToolResultCacheSummary(CogniEDABaseModel):
    """Reusable tool-result cache entry scoped to the current analytical frame."""

    cache_key: NonEmptyStr
    summary: NonEmptyStr
    status: MemoryStatus = MemoryStatus.ACTIVE
    source_type: MemorySourceType = MemorySourceType.TOOL_RESULT
    created_at: datetime
    expires_at: datetime | None = None
    source_profile_id: UUID | None = None
    code_reference: str | None = None
    invalidation_rules: list[InvalidationRule] = Field(default_factory=list)


class DataProfileContextSummary(CogniEDABaseModel):
    """Compact DataProfile summary used inside a SessionFrame."""

    profile_id: UUID
    dataset_path: NonEmptyStr
    dvc_hash: str | None = None
    dvc_version_label: str | None = None
    row_count: NonNegativeInt | None = None
    column_count: NonNegativeInt | None = None
    warning_count: NonNegativeInt = 0
    lifecycle_state: DataProfileLifecycleState = DataProfileLifecycleState.ACTIVE
    accepted_as_ground_truth: bool = False
    memory_status: MemoryStatus = MemoryStatus.ACTIVE
    provenance: list[ContextProvenance] = Field(default_factory=list)
    invalidation_rules: list[InvalidationRule] = Field(default_factory=list)
    fresh_until: datetime | None = None


class AssumptionContextSummary(CogniEDABaseModel):
    """Compact active-assumption summary for a planning context frame."""

    assumption_id: UUID
    statement: NonEmptyStr
    confidence: ConfidenceLevel
    linked_evidence_count: NonNegativeInt = 0
    memory_status: MemoryStatus = MemoryStatus.ACTIVE
    provenance: list[ContextProvenance] = Field(default_factory=list)
    invalidation_rules: list[InvalidationRule] = Field(default_factory=list)
    fresh_until: datetime | None = None


class TaskContextSummary(CogniEDABaseModel):
    """Compact Task summary used in planning context."""

    task_id: UUID
    title: NonEmptyStr
    lifecycle_state: str
    parent_task_id: UUID | None = None
    memory_status: MemoryStatus = MemoryStatus.ACTIVE
    provenance: list[ContextProvenance] = Field(default_factory=list)


class HypothesisContextSummary(CogniEDABaseModel):
    """Compact active-hypothesis summary for a session frame."""

    hypothesis_id: UUID
    statement: NonEmptyStr
    status: HypothesisStatus
    validation_method: NonEmptyStr
    linked_evidence_count: NonNegativeInt = 0
    memory_status: MemoryStatus = MemoryStatus.ACTIVE
    provenance: list[ContextProvenance] = Field(default_factory=list)
    invalidation_rules: list[InvalidationRule] = Field(default_factory=list)
    fresh_until: datetime | None = None


class EvidenceContextSummary(CogniEDABaseModel):
    """Compact Evidence summary for reuse in session context."""

    evidence_id: UUID
    evidence_type: EvidenceType
    method: NonEmptyStr
    summary: NonEmptyStr
    created_at: datetime
    lifecycle_state: EvidenceLifecycleState = EvidenceLifecycleState.ACTIVE
    memory_status: MemoryStatus = MemoryStatus.ACTIVE
    provenance: list[ContextProvenance] = Field(default_factory=list)
    invalidation_rules: list[InvalidationRule] = Field(default_factory=list)
    fresh_until: datetime | None = None


class DiscoveryContextSummary(CogniEDABaseModel):
    """Compact Discovery summary for planning context reuse."""

    discovery_id: UUID
    claim_statement: NonEmptyStr
    epistemic_status: DiscoveryEpistemicStatus
    scope: NonEmptyStr
    evidence_ids: list[UUID]
    lifecycle_state: DiscoveryLifecycleState = DiscoveryLifecycleState.ACTIVE
    memory_status: MemoryStatus = MemoryStatus.ACTIVE
    provenance: list[ContextProvenance] = Field(default_factory=list)


class UserDecisionContextSummary(CogniEDABaseModel):
    """Compact user-decision provenance summary for session context."""

    decision_id: UUID
    decision_type: UserDecisionType
    decision: NonEmptyStr
    status: UserDecisionStatus
    created_at: datetime
    memory_status: MemoryStatus = MemoryStatus.ACTIVE
    provenance: list[ContextProvenance] = Field(default_factory=list)
    invalidation_rules: list[InvalidationRule] = Field(default_factory=list)
    fresh_until: datetime | None = None
