"""Lifecycle enums for execution-owned objects."""

from enum import StrEnum


class ExecutionRunStatus(StrEnum):
    """Lifecycle states for an ExecutionRun."""

    PENDING_APPROVAL = "pending_approval"
    ADMITTED = "admitted"
    DISPATCH_CLAIMED = "dispatch_claimed"
    RUNNING = "running"
    RESULT_RECEIVED = "result_received"
    EVIDENCE_ADMITTING = "evidence_admitting"
    EVIDENCE_ADMITTED = "evidence_admitted"
    DISPATCH_FAILED = "dispatch_failed"
    EXECUTION_FAILED = "execution_failed"
    EXPIRED = "expired"
    ABANDONED = "abandoned"
    CANCELLED = "cancelled"
    RESULT_CONFLICT = "result_conflict"


class ExecutionApprovalStatus(StrEnum):
    """Durable lifecycle for one user-approved execution contract."""

    PENDING = "pending"
    APPROVED = "approved"
    CANCELLED = "cancelled"
    STALE = "stale"
    CONSUMED = "consumed"
    FAILED = "failed"
