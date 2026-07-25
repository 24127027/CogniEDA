"""Deterministic validity propagation plan construction and authority scoping."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from schemas.enums import (
    EvaluationControlState,
    ValidityEventType,
    ValiditySourceType,
)
from schemas.validity import (
    ValidityPropagationCommand,
    ValidityPropagationPlan,
)

__all__ = [
    "ALLOWED_TRUSTED_PRODUCERS",
    "EVENT_AUTHORITY",
    "EVENT_SOURCE_ALLOWLIST",
    "build_validity_propagation_plan",
    "validity_authority_scope",
]

ALLOWED_TRUSTED_PRODUCERS = {
    "system_integrity",
    "validity_propagation_service",
    "admission_service",
    "receiver_service",
}

EVENT_AUTHORITY = {
    ValidityEventType.EVIDENCE_INVALIDATION: (
        "integrity_invalidation",
        "invalidate_source",
    ),
    ValidityEventType.EVIDENCE_SUPERSESSION: (
        "supersession_propagation",
        "supersede_source",
    ),
    ValidityEventType.EVIDENCE_CONFLICT: (
        "conflict_quarantine",
        "quarantine_source",
    ),
    ValidityEventType.DATA_PROFILE_INVALIDATION: (
        "integrity_invalidation",
        "invalidate_source",
    ),
    ValidityEventType.DATA_PROFILE_SUPERSESSION: (
        "supersession_propagation",
        "supersede_source",
    ),
    ValidityEventType.ANALYSIS_FRAME_INVALIDITY: (
        "integrity_invalidation",
        "invalidate_source",
    ),
    ValidityEventType.EXECUTION_RUN_CONFLICT: (
        "conflict_quarantine",
        "quarantine_source",
    ),
    ValidityEventType.PROVENANCE_CORRUPTION: (
        "integrity_invalidation",
        "invalidate_source",
    ),
}

EVENT_SOURCE_ALLOWLIST = {
    ValidityEventType.EVIDENCE_INVALIDATION: {ValiditySourceType.EVIDENCE},
    ValidityEventType.EVIDENCE_SUPERSESSION: {ValiditySourceType.EVIDENCE},
    ValidityEventType.EVIDENCE_CONFLICT: {ValiditySourceType.EVIDENCE},
    ValidityEventType.DATA_PROFILE_INVALIDATION: {ValiditySourceType.DATA_PROFILE},
    ValidityEventType.DATA_PROFILE_SUPERSESSION: {ValiditySourceType.DATA_PROFILE},
    ValidityEventType.ANALYSIS_FRAME_INVALIDITY: {ValiditySourceType.ANALYSIS_FRAME},
    ValidityEventType.EXECUTION_RUN_CONFLICT: {ValiditySourceType.EXECUTION_RUN},
    ValidityEventType.PROVENANCE_CORRUPTION: {
        ValiditySourceType.ANALYSIS_FRAME,
        ValiditySourceType.EXECUTION_RUN,
    },
}

ACTIVE_EVALUATION_STATES = {
    EvaluationControlState.PENDING,
    EvaluationControlState.CLAIMED,
    EvaluationControlState.PROPOSAL_READY,
    EvaluationControlState.RETRYABLE_FAILED,
    EvaluationControlState.COMMITTED,
}


def validity_authority_scope(
    *,
    event_type: ValidityEventType,
    source_type: ValiditySourceType,
    source_id: UUID,
    replacement_id: UUID | None = None,
) -> tuple[str, str]:
    """Return the exact durable capability scope for one source event."""

    purpose, operation = EVENT_AUTHORITY[event_type]
    source_scope = f"{source_type.value}:{source_id}"
    if replacement_id is not None:
        source_scope = f"{source_scope}:{replacement_id}"
    return purpose, f"{operation}:{source_scope}"


def build_validity_propagation_plan(
    session: Session,
    command: ValidityPropagationCommand,
    *,
    principal_id: str | None = None,
) -> ValidityPropagationPlan:
    """Construct a detached validity propagation plan without mutating state."""

    from application.validity.propagation_service import AtomicValidityPropagationService

    service = AtomicValidityPropagationService(session, principal_id=principal_id)
    return service.plan_propagation(command)
