"""SQLModel table definitions for execution-owned records."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

from db.models.common import utc_now
from schemas.enums import ExecutionApprovalStatus, ValiditySourceState


class ExecutionRunRecord(SQLModel, table=True):
    """Minimal provenance record for one executor attempt."""

    __tablename__ = "execution_runs"
    __table_args__ = (
        UniqueConstraint("previous_attempt_id", name="uq_execution_runs_previous_attempt_id"),
    )

    execution_run_id: UUID = Field(default_factory=uuid4, primary_key=True)
    task_id: UUID | None = Field(default=None, foreign_key="tasks.task_id", index=True)
    hypothesis_id: UUID | None = Field(
        default=None,
        foreign_key="hypotheses.hypothesis_id",
        index=True,
    )
    analysis_frame_id: UUID | None = Field(
        default=None,
        foreign_key="analysis_frames.analysis_frame_id",
        index=True,
    )
    executor_type: str | None = Field(default=None, index=True)
    method_id: str | None = Field(default=None, index=True)
    parameter_hash: str | None = Field(default=None, index=True)
    status: str = Field(default="pending_approval", index=True, nullable=False)
    validity_state: ValiditySourceState = Field(
        default=ValiditySourceState.ACTIVE,
        nullable=False,
        index=True,
    )
    validity_reason: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    dispatch_idempotency_key: str | None = Field(default=None, index=True)
    worker_id: str | None = Field(default=None, index=True)
    lease_epoch: int = Field(default=0, nullable=False)
    lease_acquired_at: datetime | None = Field(default=None)
    lease_expires_at: datetime | None = Field(default=None)

    attempt_version: int = Field(default=1, nullable=False)
    finalizer_owner_id: str | None = Field(default=None, index=True)
    finalization_fencing_epoch: int | None = Field(default=None)
    finalization_claimed_at: datetime | None = Field(default=None)
    finalization_expires_at: datetime | None = Field(default=None)

    previous_attempt_id: UUID | None = Field(
        default=None, foreign_key="execution_runs.execution_run_id", index=True
    )
    retry_reason: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    retry_authorization_metadata: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )
    recovery_status: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)


class ExecutionOutboxRecord(SQLModel, table=True):
    """Durable dispatch intent to bridge Planner transaction and executor call."""

    __tablename__ = "execution_outbox"
    __table_args__ = (
        UniqueConstraint("execution_run_id", name="uq_execution_outbox_execution_run_id"),
    )

    outbox_id: UUID = Field(default_factory=uuid4, primary_key=True)
    execution_run_id: UUID = Field(
        foreign_key="execution_runs.execution_run_id",
        nullable=False,
        index=True,
    )
    dispatch_idempotency_key: str = Field(index=True, nullable=False)
    executor_type: str = Field(nullable=False)
    method_id: str = Field(nullable=False)
    parameter_hash: str = Field(nullable=False)
    prepared_payload: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    status: str = Field(default="pending", index=True, nullable=False)
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)
    dispatched_at: datetime | None = Field(default=None)


class ExecutionInboxRecord(SQLModel, table=True):
    """Durable executor result envelope for scientific finalization."""

    __tablename__ = "execution_inbox"
    __table_args__ = (
        UniqueConstraint(
            "execution_run_id",
            "dispatch_idempotency_key",
            "result_digest",
            name="uq_execution_inbox_digest",
        ),
    )

    inbox_id: UUID = Field(default_factory=uuid4, primary_key=True)
    execution_run_id: UUID = Field(
        foreign_key="execution_runs.execution_run_id",
        nullable=False,
        index=True,
    )
    dispatch_idempotency_key: str = Field(index=True, nullable=False)
    lease_epoch: int = Field(nullable=False)
    result_digest: str = Field(nullable=False, index=True)
    executor_status: str = Field(nullable=False)
    serialized_observations: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    error_message: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    method_id: str = Field(nullable=False)
    producer_identity: str | None = Field(default=None)
    status: str = Field(default="pending", index=True, nullable=False)
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)
    processed_at: datetime | None = Field(default=None)


class ExecutionApprovalRecord(SQLModel, table=True):
    """Durable approval boundary for one prepared execution contract."""

    __tablename__ = "execution_approvals"

    execution_approval_id: UUID = Field(default_factory=uuid4, primary_key=True)
    session_id: str = Field(index=True, nullable=False)
    task_id: UUID = Field(foreign_key="tasks.task_id", nullable=False, index=True)
    profile_id: UUID = Field(foreign_key="data_profiles.profile_id", nullable=False, index=True)
    hypothesis_id: UUID | None = Field(
        default=None, foreign_key="hypotheses.hypothesis_id", index=True
    )
    execution_ref: str = Field(index=True, nullable=False)
    contract_fingerprint: str = Field(index=True, nullable=False)
    prepared_payload: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    status: ExecutionApprovalStatus = Field(
        default=ExecutionApprovalStatus.PENDING, nullable=False, index=True
    )
    execution_run_id: UUID | None = Field(
        default=None, foreign_key="execution_runs.execution_run_id", index=True
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)
