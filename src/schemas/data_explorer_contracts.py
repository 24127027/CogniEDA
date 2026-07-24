"""Observation-only contracts for the Data Explorer execution boundary."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, NonNegativeInt

from schemas.common import CogniEDABaseModel, ImmutableCogniEDABaseModel, NonEmptyStr
from schemas.execution_observations import AnalysisFrameObservation, EvidenceObservation


class TechnicalDiagnostic(ImmutableCogniEDABaseModel):
    """One bounded technical diagnostic with no scientific authority."""

    code: NonEmptyStr
    message: NonEmptyStr


class ExecutionDetails(ImmutableCogniEDABaseModel):
    """Non-authoritative execution facts needed to interpret or reproduce observations."""

    deterministic_seed: int | None = None
    source_sample_size: NonNegativeInt | None = None
    effective_sample_size: NonNegativeInt | None = None
    exclusions: tuple[NonEmptyStr, ...] = ()
    missing_data_policy: str | None = None
    technical_limitations: tuple[NonEmptyStr, ...] = ()


class DataExplorerSuccessResult(CogniEDABaseModel):
    """Observation-only result returned by Data Explorer after successful execution."""

    status: Literal["success"] = "success"
    analysis_frame: AnalysisFrameObservation
    evidence_observation: EvidenceObservation
    execution_details: ExecutionDetails = Field(default_factory=ExecutionDetails)
    execution_diagnostics: tuple[TechnicalDiagnostic, ...] = ()


class DataExplorerFailureReason(StrEnum):
    """Typed technical failure categories reported by Data Explorer."""

    DATA_ACCESS_FAILURE = "data_access_failure"
    INVALID_EXECUTION_CONTRACT = "invalid_execution_contract"
    METHOD_UNAVAILABLE = "method_unavailable"
    METHOD_EXECUTION_FAILURE = "method_execution_failure"
    ARTIFACT_WRITE_FAILURE = "artifact_write_failure"


class TechnicalRetryDisposition(StrEnum):
    """Diagnostic retryability; application services retain retry authority."""

    UNDETERMINED = "undetermined"
    RETRYABLE = "retryable"
    NOT_RETRYABLE = "not_retryable"


class DataExplorerFailureResult(CogniEDABaseModel):
    """Technical failure outcome with no Evidence or scientific evaluation."""

    status: Literal["failed"] = "failed"
    failure_reason: DataExplorerFailureReason
    message: NonEmptyStr
    retry_disposition: TechnicalRetryDisposition = TechnicalRetryDisposition.UNDETERMINED
    technical_limitations: tuple[NonEmptyStr, ...] = ()
    diagnostics: tuple[TechnicalDiagnostic, ...] = ()
    artifact_refs: tuple[NonEmptyStr, ...] = ()
    log_refs: tuple[NonEmptyStr, ...] = ()


type DataExplorerResult = Annotated[
    DataExplorerSuccessResult | DataExplorerFailureResult,
    Field(discriminator="status"),
]
