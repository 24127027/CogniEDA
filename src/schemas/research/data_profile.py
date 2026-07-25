"""Canonical DataProfile schema and structural summary models."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import Field, NonNegativeInt

from schemas.common import (
    BaselineSummary,
    CategoricalColumnSummary,
    ColumnSchemaSummary,
    ImmutableCogniEDABaseModel,
    LineageStep,
    NonEmptyStr,
    NumericColumnSummary,
    QualityFlag,
    SchemaSummary,
    TopValueSummary,
    utc_now,
)
from schemas.research.lifecycle import (
    DataProfileLifecycleState,
    DataProfileMethod,
    DatasetSourceType,
)

__all__ = [
    "BaselineSummary",
    "CategoricalColumnSummary",
    "ColumnSchemaSummary",
    "DataProfile",
    "LineageStep",
    "NumericColumnSummary",
    "QualityFlag",
    "SchemaSummary",
    "TopValueSummary",
]


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
    lifecycle_reason: str | None = None
    accepted_as_ground_truth: bool = False
    created_at: datetime = Field(default_factory=utc_now)
