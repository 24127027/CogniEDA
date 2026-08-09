"""SQLModel table definitions for persisted CogniEDA research state."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

from cognieda.schemas.enums import (
    DiscoveryEpistemicStatus,
    DiscoveryLifecycleState,
    ExecutionApprovalStatus,
    HypothesisStatus,
    ObjectiveStatus,
    PlannerNodeName,
    PlannerOperationApprovalState,
    PlannerOperationType,
    TaskStatus,
    UserDecisionStatus,
    UserDecisionType,
)


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp for persisted rows."""

    return datetime.now(UTC)


class TimestampedRecord(SQLModel):
    """Shared timestamp fields for persisted rows with lifecycle transitions."""

    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)


class ObjectiveRecord(SQLModel, table=True):
    """Bounded SQLite mapping for the MVP Objective contract."""

    __tablename__ = "objectives"

    objective_id: UUID = Field(default_factory=uuid4, primary_key=True)
    text: str = Field(sa_column=Column(Text, nullable=False))


class ObjectiveRevisionRecord(SQLModel, table=True):
    """Minimal provenance record for one Objective refinement."""

    __tablename__ = "objective_revisions"

    objective_revision_id: UUID = Field(default_factory=uuid4, primary_key=True)
    objective_id: UUID = Field(
        foreign_key="objectives.objective_id",
        nullable=False,
        index=True,
    )
    previous_title: str = Field(sa_column=Column(Text, nullable=False))
    previous_description: str = Field(sa_column=Column(Text, nullable=False))
    previous_lifecycle_state: ObjectiveStatus | None = Field(
        default=None,
        nullable=True,
        index=True,
    )
    new_title: str = Field(sa_column=Column(Text, nullable=False))
    new_description: str = Field(sa_column=Column(Text, nullable=False))
    new_lifecycle_state: ObjectiveStatus | None = Field(
        default=None,
        nullable=True,
        index=True,
    )
    changed_fields: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    revision_reason: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    planner_operation_id: str | None = Field(default=None, index=True)
    user_decision_id: str | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)
    created_by: str | None = Field(default=None, index=True)


class DataProfileRecord(SQLModel, table=True):
    """Bounded SQLite mapping for an immutable MVP DataProfile snapshot."""

    __tablename__ = "data_profiles"

    data_profile_id: UUID = Field(default_factory=uuid4, primary_key=True)
    row_count: int = Field(ge=0, nullable=False)
    column_count: int = Field(ge=0, nullable=False)
    columns: list[dict[str, Any]] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )


class AssumptionRecord(SQLModel, table=True):
    """Bounded SQLite mapping for the planning-only MVP Assumption."""

    __tablename__ = "assumptions"

    assumption_id: UUID = Field(default_factory=uuid4, primary_key=True)
    text: str = Field(sa_column=Column(Text, nullable=False))


class TaskRecord(SQLModel, table=True):
    """Bounded SQLite mapping for the MVP Task lifecycle."""

    __tablename__ = "tasks"

    task_id: UUID = Field(default_factory=uuid4, primary_key=True)
    instruction: str = Field(sa_column=Column(Text, nullable=False))
    status: TaskStatus = Field(default=TaskStatus.PENDING, nullable=False, index=True)


class HypothesisRecord(TimestampedRecord, table=True):
    """Persisted Hypothesis FCO."""

    __tablename__ = "hypotheses"
    __table_args__ = (UniqueConstraint("task_id", name="uq_hypotheses_task_id"),)

    hypothesis_id: UUID = Field(default_factory=uuid4, primary_key=True)
    task_id: UUID = Field(foreign_key="tasks.task_id", nullable=False, index=True)
    profile_id: UUID = Field(
        foreign_key="data_profiles.data_profile_id", nullable=False, index=True
    )
    statement: str = Field(sa_column=Column(Text, nullable=False))
    variables: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    scope: str = Field(sa_column=Column(Text, nullable=False))
    validation_method: str = Field(sa_column=Column(Text, nullable=False))
    evidence_expectation: str = Field(sa_column=Column(Text, nullable=False))
    status: HypothesisStatus = Field(default=HypothesisStatus.PROPOSED, nullable=False, index=True)


class AnalysisFrameRecord(SQLModel, table=True):
    """Minimal provenance record for the data view used by an analysis."""

    __tablename__ = "analysis_frames"

    analysis_frame_id: UUID = Field(default_factory=uuid4, primary_key=True)
    data_profile_id: UUID = Field(
        foreign_key="data_profiles.data_profile_id",
        nullable=False,
        index=True,
    )
    frame_hash: str | None = Field(default=None, index=True)
    frame_ref: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    column_refs: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    row_filter_description: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)


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
    dispatch_idempotency_key: str | None = Field(default=None, index=True)
    worker_id: str | None = Field(default=None, index=True)
    lease_epoch: int = Field(default=0, nullable=False)
    lease_acquired_at: datetime | None = Field(default=None)
    lease_expires_at: datetime | None = Field(default=None)
    attempt_version: int = Field(default=1, nullable=False)
    previous_attempt_id: UUID | None = Field(
        default=None,
        foreign_key="execution_runs.execution_run_id",
        index=True,
    )
    retry_reason: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    retry_authorization_metadata: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    recovery_status: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)


class ExecutionOutboxRecord(SQLModel, table=True):
    """One durable dispatch intent for exactly one execution attempt."""

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
    dispatch_idempotency_key: str = Field(nullable=False, index=True)
    executor_type: str = Field(nullable=False)
    method_id: str = Field(nullable=False)
    parameter_hash: str = Field(nullable=False)
    prepared_payload: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    status: str = Field(default="pending", nullable=False, index=True)
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)
    dispatched_at: datetime | None = Field(default=None)


class ExecutionApprovalRecord(SQLModel, table=True):
    """Durable user-approval record for one prepared execution contract."""

    __tablename__ = "execution_approvals"

    execution_approval_id: UUID = Field(default_factory=uuid4, primary_key=True)
    session_id: str = Field(nullable=False, index=True)
    task_id: UUID = Field(foreign_key="tasks.task_id", nullable=False, index=True)
    profile_id: UUID = Field(
        foreign_key="data_profiles.data_profile_id", nullable=False, index=True
    )
    hypothesis_id: UUID | None = Field(
        default=None,
        foreign_key="hypotheses.hypothesis_id",
        index=True,
    )
    execution_ref: str = Field(nullable=False, index=True)
    contract_fingerprint: str = Field(nullable=False, index=True)
    prepared_payload: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    status: ExecutionApprovalStatus = Field(
        default=ExecutionApprovalStatus.PENDING,
        nullable=False,
        index=True,
    )
    execution_run_id: UUID | None = Field(
        default=None,
        foreign_key="execution_runs.execution_run_id",
        index=True,
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)


class EvidenceRecord(SQLModel, table=True):
    """Bounded SQLite mapping for direct MVP Evidence lineage."""

    __tablename__ = "evidence"

    evidence_id: UUID = Field(default_factory=uuid4, primary_key=True)
    task_id: UUID = Field(foreign_key="tasks.task_id", nullable=False, index=True)
    data_profile_id: UUID = Field(
        foreign_key="data_profiles.data_profile_id", nullable=False, index=True
    )
    content: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    provenance: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    artifact_refs: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))


class DiscoveryRecord(SQLModel, table=True):
    """Persisted immutable Discovery FCO."""

    __tablename__ = "discoveries"
    __table_args__ = (UniqueConstraint("hypothesis_id", name="uq_discoveries_hypothesis_id"),)

    discovery_id: UUID = Field(default_factory=uuid4, primary_key=True)
    hypothesis_id: UUID = Field(foreign_key="hypotheses.hypothesis_id", nullable=False, index=True)
    evidence_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    claim: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    epistemic_status: DiscoveryEpistemicStatus = Field(nullable=False, index=True)
    scope: str = Field(sa_column=Column(Text, nullable=False))
    validity_basis: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    lifecycle_state: DiscoveryLifecycleState = Field(
        default=DiscoveryLifecycleState.ACTIVE,
        nullable=False,
        index=True,
    )
    review_reasons: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    flagged_by_evidence_ids: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)


class UserDecisionRecord(TimestampedRecord, table=True):
    """Typed provenance for a user decision."""

    __tablename__ = "user_decisions"

    decision_id: UUID = Field(default_factory=uuid4, primary_key=True)
    decision_type: UserDecisionType = Field(nullable=False, index=True)
    decision: str = Field(sa_column=Column(Text, nullable=False))
    rationale: str = Field(sa_column=Column(Text, nullable=False))
    status: UserDecisionStatus = Field(
        default=UserDecisionStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    alternatives_considered: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    related_task_ids: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    related_hypothesis_ids: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    superseded_by_decision_id: UUID | None = Field(
        default=None,
        foreign_key="user_decisions.decision_id",
    )


class PlannerOperationRecord(SQLModel, table=True):
    """Persisted pending mutation produced by planner nodes."""

    __tablename__ = "planner_operations"

    operation_id: UUID = Field(default_factory=uuid4, primary_key=True)
    session_id: str | None = Field(default=None, index=True)
    operation_type: PlannerOperationType = Field(nullable=False, index=True)
    target_object_id: UUID | None = Field(default=None, index=True)
    target_object_type: str | None = Field(default=None, index=True)
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    produced_by_node: PlannerNodeName = Field(nullable=False, index=True)
    requires_user_approval: bool = Field(default=True, nullable=False, index=True)
    approval_state: PlannerOperationApprovalState = Field(
        default=PlannerOperationApprovalState.PENDING,
        nullable=False,
        index=True,
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)
    committed_at: datetime | None = Field(default=None, nullable=True)
    approved_at: datetime | None = Field(default=None, nullable=True)
    error_message: str | None = Field(default=None, sa_column=Column(Text, nullable=True))


class SessionFrameRecord(SQLModel, table=True):
    """Internal SQLite envelope for one serialized MVP SessionFrame snapshot."""

    __tablename__ = "session_frames"

    session_frame_id: UUID = Field(default_factory=uuid4, primary_key=True)
    state: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)
