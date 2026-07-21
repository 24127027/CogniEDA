"""Minimal non-FCO provenance records."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from schemas.common import CogniEDABaseModel, NonEmptyStr, utc_now
from schemas.enums import ExecutionApprovalStatus, ExecutionRunStatus, ObjectiveStatus


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
    status: NonEmptyStr = ExecutionRunStatus.PENDING_APPROVAL.value
    dispatch_idempotency_key: NonEmptyStr | None = None
    worker_id: NonEmptyStr | None = None
    lease_epoch: int = 0
    lease_acquired_at: datetime | None = None
    lease_expires_at: datetime | None = None
    attempt_version: int = 1
    previous_attempt_id: UUID | None = None
    retry_reason: NonEmptyStr | None = None
    retry_authorization_metadata: dict[str, Any] | None = None
    recovery_status: NonEmptyStr | None = None
    created_at: datetime = Field(default_factory=utc_now)


class ExecutionOutbox(CogniEDABaseModel):
    """Durable dispatch intent created atomically with an admitted attempt."""

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


class ExecutionApproval(CogniEDABaseModel):
    """Durable, session-bound approval record for an execution contract."""

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


class ObjectiveRevision(CogniEDABaseModel):
    """Minimal provenance record for one Objective refinement."""

    objective_revision_id: UUID = Field(default_factory=uuid4)
    objective_id: UUID
    previous_title: NonEmptyStr
    previous_description: NonEmptyStr
    previous_lifecycle_state: ObjectiveStatus | None = None
    new_title: NonEmptyStr
    new_description: NonEmptyStr
    new_lifecycle_state: ObjectiveStatus | None = None
    changed_fields: list[NonEmptyStr] = Field(default_factory=list)
    revision_reason: str | None = None
    planner_operation_id: str | None = None
    user_decision_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    created_by: str | None = None
