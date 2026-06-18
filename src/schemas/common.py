"""Shared value objects and helpers for CogniEDA schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, NonNegativeFloat, NonNegativeInt

from schemas.enums import QualityFlagSeverity

NonEmptyStr: TypeAlias = Annotated[str, Field(min_length=1)]
ScalarParameterValue: TypeAlias = str | int | float | bool | None


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


class CogniEDABaseModel(BaseModel):
    """Shared base model for all CogniEDA schema objects."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_assignment=True)


class MethodParameter(CogniEDABaseModel):
    """Typed method parameter entry used instead of ad hoc dictionaries."""

    name: NonEmptyStr
    value: ScalarParameterValue


class ColumnSchemaSummary(CogniEDABaseModel):
    """Schema-level summary for a single inferred dataset column."""

    name: NonEmptyStr
    inferred_dtype: NonEmptyStr
    nullable: bool
    distinct_count: NonNegativeInt | None = None
    missing_count: NonNegativeInt | None = None


class SchemaSummary(CogniEDABaseModel):
    """Structural schema summary inferred from a dataset version."""

    columns: list[ColumnSchemaSummary] = Field(default_factory=list)
    detected_primary_key: str | None = None
    inferred_time_columns: list[NonEmptyStr] = Field(default_factory=list)


class BaselineSummary(CogniEDABaseModel):
    """Baseline row-level quality summary for a profiled dataset."""

    missing_cell_count: NonNegativeInt = 0
    missing_cell_ratio: NonNegativeFloat = Field(default=0.0, le=1.0)
    duplicate_row_count: NonNegativeInt = 0
    duplicate_row_ratio: NonNegativeFloat = Field(default=0.0, le=1.0)


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
