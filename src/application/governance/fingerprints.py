"""Pure deterministic governance fingerprint helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from schemas.canonical import canonical_sha256
from schemas.enums import AuthorizationClass, GovernanceDecisionOutcome


def compute_governance_authority_fingerprint(
    *,
    authority_id: UUID,
    actor_identity: str,
    authority_class: AuthorizationClass,
    workspace_id: str,
    session_id: str | None,
    purpose: str,
    operation_type: str,
    issued_by: str,
    issued_at: datetime,
    expires_at: datetime | None,
) -> str:
    """Fingerprint one independently issued durable actor-authority grant."""

    return canonical_sha256(
        {
            "actor_identity": actor_identity,
            "authority_class": authority_class.value,
            "authority_id": authority_id,
            "expires_at": _canonical_datetime(expires_at),
            "issued_at": _canonical_datetime(issued_at),
            "issued_by": issued_by,
            "operation_type": operation_type,
            "purpose": purpose,
            "session_id": session_id,
            "workspace_id": workspace_id,
        }
    )


def compute_decision_fingerprint(
    *,
    decision_id: UUID,
    authority_id: UUID,
    evaluation_id: UUID,
    evaluation_key: str,
    hypothesis_id: UUID,
    task_id: UUID,
    proposal_digest: str,
    bundle_digest: str,
    evidence_set_digest: str,
    decision: GovernanceDecisionOutcome,
    actor: str,
    actor_authority_type: AuthorizationClass,
    workspace_id: str,
    session_id: str | None,
    purpose: str,
    operation_type: str,
    decision_timestamp: datetime,
    reason: str | None,
) -> str:
    """Fingerprint every immutable field of one durable governance decision."""

    return canonical_sha256(
        {
            "actor": actor,
            "actor_authority_type": actor_authority_type.value,
            "authority_id": authority_id,
            "bundle_digest": bundle_digest,
            "decision": decision.value,
            "decision_id": decision_id,
            "decision_timestamp": _canonical_datetime(decision_timestamp),
            "evaluation_id": evaluation_id,
            "evaluation_key": evaluation_key,
            "evidence_set_digest": evidence_set_digest,
            "hypothesis_id": hypothesis_id,
            "operation_type": operation_type,
            "proposal_digest": proposal_digest,
            "purpose": purpose,
            "reason": reason,
            "session_id": session_id,
            "task_id": task_id,
            "workspace_id": workspace_id,
        }
    )

def _canonical_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def _datetime_is_expired(expiry: datetime | None, now: datetime) -> bool:
    if expiry is None:
        return False
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    return expiry <= now
