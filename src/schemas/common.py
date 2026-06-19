"""Shared value objects and helpers for CogniEDA schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, NonNegativeFloat, NonNegativeInt

from schemas.enums import QualityFlagSeverity

type NonEmptyStr = Annotated[str, Field(min_length=1)]
type ScalarParameterValue = str | int | float | bool | None


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(UTC)


class CogniEDABaseModel(BaseModel):
    """Shared base model for all CogniEDA schema objects."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_assignment=True)


class MethodParameter(CogniEDABaseModel):
    """Typed method parameter entry used instead of ad hoc dictionaries."""

    name: NonEmptyStr
    value: ScalarParameterValue


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
    """Schema-level summary for a single inferred dataset column."""

    name: NonEmptyStr
    inferred_dtype: NonEmptyStr
    nullable: bool
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


class EvidenceProvenance(CogniEDABaseModel):
    """Provenance fields that explain how an evidence record was produced."""

    dataset_version: NonEmptyStr
    source_profile_id: str | None = None
    execution_label: str | None = None
    code_reference: str | None = None
    artifact_paths: list[NonEmptyStr] = Field(default_factory=list)


class EvidenceResultSummary(CogniEDABaseModel):
    """Compact, typed result summary for an evidence record."""

    summary: NonEmptyStr
    key_findings: list[NonEmptyStr] = Field(default_factory=list)
    metric_name: str | None = None
    metric_value: ScalarParameterValue = None
    metric_unit: str | None = None


class DatasetContextSummary(CogniEDABaseModel):
    """Compact dataset summary used inside a session frame."""

    dataset_id: str
    name: NonEmptyStr
    version: NonEmptyStr
    kind: NonEmptyStr
    role: NonEmptyStr
    row_count: NonNegativeInt | None = None
    column_count: NonNegativeInt | None = None
    warning_count: NonNegativeInt = 0


class AssumptionContextSummary(CogniEDABaseModel):
    """Compact active-assumption summary for a session frame."""

    assumption_id: str
    statement: NonEmptyStr
    confidence: NonEmptyStr
    linked_evidence_count: NonNegativeInt = 0


class HypothesisContextSummary(CogniEDABaseModel):
    """Compact active-hypothesis summary for a session frame."""

    hypothesis_id: str
    statement: NonEmptyStr
    status: NonEmptyStr
    validation_method: NonEmptyStr
    linked_evidence_count: NonNegativeInt = 0


class EvidenceContextSummary(CogniEDABaseModel):
    """Compact evidence summary for reuse in session memory."""

    evidence_id: str
    evidence_type: NonEmptyStr
    method: NonEmptyStr
    summary: NonEmptyStr
    created_at: datetime


class DecisionContextSummary(CogniEDABaseModel):
    """Compact decision summary for reuse in session memory."""

    decision_id: str
    decision_type: NonEmptyStr
    decision: NonEmptyStr
    status: NonEmptyStr
    created_at: datetime
