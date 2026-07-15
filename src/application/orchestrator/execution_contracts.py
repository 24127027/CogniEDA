"""Transport contracts shared by durable execution admission and finalization."""

from __future__ import annotations

from secrets import token_urlsafe
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from schemas.common import EvaluationThresholds, EvidenceResultSummary, MethodParameter
from schemas.enums import EvidenceType, HypothesisEvidenceOutcome


class HypothesisDraft(BaseModel):
    """Transient hypothesis contract without a durable Hypothesis identity."""

    statement: str
    variables: list[str] = Field(default_factory=list)
    scope: str
    validation_method: str
    evidence_expectation: str


class ExecutionSpecification(BaseModel):
    """Executor-facing analytical method contract without persistent FCO references."""

    claim_type: Literal["association"]
    variable_bindings: list[str] = Field(default_factory=list)
    scope: str
    evidence_expectation: str
    decision_rule: EvaluationThresholds
    validation_method: str
    executor_id: str
    method_parameters: list[MethodParameter] = Field(default_factory=list)


class PreparedExecution(BaseModel):
    """Typed executor contract reconstructed from durable admission state."""

    execution_ref: str = Field(default_factory=lambda: f"execution:{token_urlsafe(9)}")
    task_ref: str
    data_profile_ref: str
    hypothesis_ref: str | None = None
    execution_run_ref: str | None = None
    task_title: str
    dataset_path: str
    hypothesis: HypothesisDraft
    specification: ExecutionSpecification
    deterministic_seed: int | None = None
    contract_fingerprint: str
    execution_run_id: UUID | None = None
    dispatch_idempotency_key: str | None = None
    lease_epoch: int | None = None


class AnalysisFrameObservation(BaseModel):
    """Executor-provided analysis-view facts before provenance is materialized."""

    frame_hash: str | None = None
    frame_ref: str | None = None
    column_refs: list[str] = Field(default_factory=list)
    row_filter_description: str | None = None

    @model_validator(mode="after")
    def _has_frame_identity(self) -> AnalysisFrameObservation:
        if self.frame_hash is None and self.frame_ref is None:
            raise ValueError("Analysis frame observation requires frame_hash or frame_ref.")
        return self


class ExecutionRunObservation(BaseModel):
    """Executor-provided run facts before durable provenance is materialized."""

    executor_type: str | None = None
    method_id: str | None = None
    parameter_hash: str | None = None
    status: str = "pending"


class EvidenceObservation(BaseModel):
    """Observed result returned by an executor before Evidence is authored at review."""

    evidence_type: EvidenceType
    method: str
    parameters: list[MethodParameter] = Field(default_factory=list)
    result_summary: EvidenceResultSummary
    artifact_refs: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    code_reference: str | None = None
    environment_reference: str | None = None


class HypothesisEvaluationDraft(BaseModel):
    """Executor evaluation linked to the current local execution rather than a UUID."""

    outcome: HypothesisEvidenceOutcome
    note: str | None = None
    finalize: bool = False


class ExecutorResult(BaseModel):
    """Typed executor outcome; failures cannot carry observed Evidence."""

    status: Literal["completed", "failed"]
    analysis_frame: AnalysisFrameObservation
    execution_run: ExecutionRunObservation
    evidence_observation: EvidenceObservation | None = None
    evaluation: HypothesisEvaluationDraft | None = None
    error_message: str | None = None

    @model_validator(mode="after")
    def _validate_completed_result(self) -> ExecutorResult:
        if self.execution_run.status != self.status:
            raise ValueError(
                "Executor result status must match its ExecutionRun observation status."
            )
        if self.status == "completed" and (
            self.evidence_observation is None or self.evaluation is None
        ):
            raise ValueError("Completed executor results require Evidence and evaluation.")
        if self.status == "failed":
            if self.evidence_observation is not None:
                raise ValueError("Failed executor results must not carry observed Evidence.")
            if not self.error_message:
                raise ValueError("Failed executor results require failure information.")
        return self
