"""Transport contracts shared by durable execution admission and finalization."""

from __future__ import annotations

from secrets import token_urlsafe
from typing import Literal
from uuid import UUID

from pydantic import Field

from schemas.common import CogniEDABaseModel, EvaluationThresholds, MethodParameter
from schemas.data_explorer_contracts import DataExplorerResult
from schemas.execution_observations import (
    AnalysisFrameObservation as AnalysisFrameObservation,
)
from schemas.execution_observations import (
    EvidenceObservation as EvidenceObservation,
)


class HypothesisDraft(CogniEDABaseModel):
    """Transient hypothesis contract without a durable Hypothesis identity."""

    statement: str
    variables: list[str] = Field(default_factory=list)
    scope: str
    validation_method: str
    evidence_expectation: str


class ExecutionSpecification(CogniEDABaseModel):
    """Executor-facing analytical method contract without persistent FCO references."""

    claim_type: Literal["association"]
    variable_bindings: list[str] = Field(default_factory=list)
    scope: str
    evidence_expectation: str
    decision_rule: EvaluationThresholds
    validation_method: str
    executor_id: str
    method_parameters: list[MethodParameter] = Field(default_factory=list)


class PreparedExecution(CogniEDABaseModel):
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


type ExecutionReceiptEnvelope = DataExplorerResult
