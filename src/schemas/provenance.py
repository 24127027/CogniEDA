"""Minimal non-FCO provenance records."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from schemas.common import CogniEDABaseModel, NonEmptyStr, utc_now
from schemas.enums import ExecutionApprovalStatus, ExecutionRunStatus


class AnalysisFrame(CogniEDABaseModel):
    """Provenance pointer for the data view used by an analysis."""

    analysis_frame_id: UUID = Field(default_factory=uuid4)
    data_profile_id: UUID
    frame_hash: NonEmptyStr | None = None
    frame_ref: NonEmptyStr | None = None
    column_refs: list[NonEmptyStr] = Field(default_factory=list)
    row_filter_description: str | None = None
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _has_frame_identity(self) -> AnalysisFrame:
        """Require at least one stable way to identify the analysis view."""

        if self.frame_hash is None and self.frame_ref is None:
            raise ValueError("AnalysisFrame requires frame_hash or frame_ref.")
        return self


class ExecutionRun(CogniEDABaseModel):
    """Provenance pointer for one executor attempt."""

    execution_run_id: UUID = Field(default_factory=uuid4)
    task_id: UUID | None = None
    hypothesis_id: UUID | None = None
    analysis_frame_id: UUID | None = None
    executor_type: NonEmptyStr | None = None
    method_id: NonEmptyStr | None = None
    parameter_hash: NonEmptyStr | None = None
    status: ExecutionRunStatus = ExecutionRunStatus.PENDING_APPROVAL

    dispatch_idempotency_key: NonEmptyStr | None = None
    worker_id: NonEmptyStr | None = None
    lease_epoch: int = 0
    lease_acquired_at: datetime | None = None
    lease_expires_at: datetime | None = None

    attempt_version: int = 1
    finalizer_owner_id: NonEmptyStr | None = None
    finalization_fencing_epoch: int | None = None
    finalization_claimed_at: datetime | None = None
    finalization_expires_at: datetime | None = None

    previous_attempt_id: UUID | None = None
    retry_reason: NonEmptyStr | None = None
    retry_authorization_metadata: dict[str, Any] | None = None
    recovery_status: NonEmptyStr | None = None

    created_at: datetime = Field(default_factory=utc_now)


class ExecutionOutbox(CogniEDABaseModel):
    """Durable dispatch intent to bridge Planner transaction and executor call."""

    outbox_id: UUID = Field(default_factory=uuid4)
    execution_run_id: UUID
    dispatch_idempotency_key: NonEmptyStr
    executor_type: NonEmptyStr
    method_id: NonEmptyStr
    parameter_hash: NonEmptyStr
    prepared_payload: dict[str, Any] = Field(default_factory=dict)
    status: NonEmptyStr = "pending"
    created_at: datetime = Field(default_factory=utc_now)
    dispatched_at: datetime | None = None


class ExecutionInbox(CogniEDABaseModel):
    """Durable executor result envelope for scientific finalization."""

    inbox_id: UUID = Field(default_factory=uuid4)
    execution_run_id: UUID
    dispatch_idempotency_key: NonEmptyStr
    lease_epoch: int
    result_digest: NonEmptyStr
    executor_status: NonEmptyStr
    serialized_observations: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    method_id: NonEmptyStr
    producer_identity: str | None = None
    status: NonEmptyStr = "pending"
    created_at: datetime = Field(default_factory=utc_now)
    processed_at: datetime | None = None


class ExecutionApproval(CogniEDABaseModel):
    """Durable workflow/provenance record for one execution approval request."""

    execution_approval_id: UUID = Field(default_factory=uuid4)
    session_id: NonEmptyStr
    task_id: UUID
    profile_id: UUID
    hypothesis_id: UUID | None = None
    execution_ref: NonEmptyStr
    contract_fingerprint: NonEmptyStr
    prepared_payload: dict[str, Any] = Field(default_factory=dict)
    status: ExecutionApprovalStatus = ExecutionApprovalStatus.PENDING
    execution_run_id: UUID | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
