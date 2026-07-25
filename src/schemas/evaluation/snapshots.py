"""Canonical snapshots for protected Hypothesis Analyst evaluation."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field, NonNegativeInt, field_validator, model_validator

from schemas.common import (
    EvaluationThresholds,
    ImmutableCogniEDABaseModel,
    MethodParameter,
    NonEmptyStr,
    ScalarParameterValue,
)
from schemas.enums import AnalysisIntent, DatasetSourceType, EvidenceType


class MethodParameterSnapshot(ImmutableCogniEDABaseModel):
    """Deeply immutable approved method parameter."""

    name: NonEmptyStr
    value: ScalarParameterValue

    def to_domain(self) -> MethodParameter:
        return MethodParameter(name=self.name, value=self.value)


class MetricThresholdSnapshot(ImmutableCogniEDABaseModel):
    """One ordered metric threshold entry."""

    name: NonEmptyStr
    value: float


class DecisionRuleSnapshot(ImmutableCogniEDABaseModel):
    """Deeply immutable approved decision rule."""

    p_value: float | None = None
    effect_size: float | None = None
    metric_thresholds: tuple[MetricThresholdSnapshot, ...] = ()
    rule_description: str | None = None

    @field_validator("metric_thresholds")
    @classmethod
    def _metric_names_are_unique_and_canonical(
        cls, value: tuple[MetricThresholdSnapshot, ...]
    ) -> tuple[MetricThresholdSnapshot, ...]:
        names = [entry.name for entry in value]
        if len(names) != len(set(names)):
            raise ValueError("Decision-rule metric threshold names must be unique.")
        if names != sorted(names):
            raise ValueError("Decision-rule metric thresholds must be sorted by name.")
        return value

    @classmethod
    def from_domain(cls, value: EvaluationThresholds) -> DecisionRuleSnapshot:
        return cls(
            p_value=value.p_value,
            effect_size=value.effect_size,
            metric_thresholds=tuple(
                MetricThresholdSnapshot(name=name, value=threshold)
                for name, threshold in sorted(value.metric_thresholds.items())
            ),
            rule_description=value.rule_description,
        )

    def to_domain(self) -> EvaluationThresholds:
        return EvaluationThresholds(
            p_value=self.p_value,
            effect_size=self.effect_size,
            metric_thresholds={entry.name: entry.value for entry in self.metric_thresholds},
            rule_description=self.rule_description,
        )


class HypothesisEvaluationSnapshot(ImmutableCogniEDABaseModel):
    """Immutable scientific content of one durably approved Hypothesis contract."""

    hypothesis_id: UUID
    data_profile_id: UUID
    statement: NonEmptyStr
    analysis_intent: AnalysisIntent
    variables: tuple[NonEmptyStr, ...] = Field(min_length=1)
    scope: NonEmptyStr
    validation_method: NonEmptyStr
    method_parameters: tuple[MethodParameterSnapshot, ...] = ()
    decision_rule: DecisionRuleSnapshot
    deterministic_seed: int | None = None
    evidence_expectation: NonEmptyStr


class DataProfileEvaluationSnapshot(ImmutableCogniEDABaseModel):
    """Safe accepted-profile metadata without a filesystem dataset locator."""

    data_profile_id: UUID
    source_type: DatasetSourceType
    version_fingerprint: NonEmptyStr
    dvc_hash: str | None = None
    dvc_version_label: str | None = None
    row_count: NonNegativeInt
    column_count: NonNegativeInt
    accepted_as_ground_truth: Literal[True] = True


class AnalysisFrameEvaluationSnapshot(ImmutableCogniEDABaseModel):
    """Immutable evaluation snapshot of one admitted AnalysisFrame."""

    analysis_frame_id: UUID
    data_profile_id: UUID
    frame_fingerprint: NonEmptyStr
    frame_hash: NonEmptyStr | None = None
    frame_ref: NonEmptyStr | None = None
    column_refs: tuple[NonEmptyStr, ...] = ()
    row_filter_description: str | None = None

    @model_validator(mode="after")
    def _has_frame_identity(self) -> AnalysisFrameEvaluationSnapshot:
        if self.frame_hash is None and self.frame_ref is None:
            raise ValueError("AnalysisFrame snapshot requires frame_hash or frame_ref.")
        return self


class ExecutionRunEvaluationSnapshot(ImmutableCogniEDABaseModel):
    """Fenced admitted-attempt provenance needed for evaluation."""

    execution_run_id: UUID
    task_id: UUID
    hypothesis_id: UUID
    analysis_frame_id: UUID
    executor_type: NonEmptyStr
    method_id: NonEmptyStr
    parameter_hash: NonEmptyStr
    attempt_version: int = Field(ge=1)
    run_fingerprint: NonEmptyStr
    status: Literal["evidence_admitted"] = "evidence_admitted"


class EvidenceResultSnapshot(ImmutableCogniEDABaseModel):
    """Deeply immutable observed result content."""

    summary: NonEmptyStr
    key_findings: tuple[NonEmptyStr, ...] = ()
    metric_name: str | None = None
    metric_value: ScalarParameterValue = None
    metric_unit: str | None = None


class AdmittedEvidenceSnapshot(ImmutableCogniEDABaseModel):
    """Deeply immutable, active Evidence input stripped of timestamps and raw artifacts."""

    evidence_id: UUID
    hypothesis_id: UUID
    data_profile_id: UUID
    analysis_frame_id: UUID
    execution_run_id: UUID
    evidence_type: EvidenceType
    method: NonEmptyStr
    parameters: tuple[MethodParameterSnapshot, ...] = ()
    result: EvidenceResultSnapshot
    limitations: tuple[NonEmptyStr, ...] = ()
    code_reference: str | None = None
    environment_reference: str | None = None
    evidence_fingerprint: NonEmptyStr
    lifecycle_state: Literal["active"] = "active"
