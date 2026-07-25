"""Governance decision schemas and record contracts."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from schemas.common import ImmutableCogniEDABaseModel, NonEmptyStr
from schemas.enums import AuthorizationClass, GovernanceDecisionOutcome


class GovernanceDecision(ImmutableCogniEDABaseModel):
    """Durable provenance for an authorized governance decision."""

    decision_id: UUID
    authority_id: UUID
    evaluation_id: UUID
    evaluation_key: NonEmptyStr
    hypothesis_id: UUID
    task_id: UUID
    proposal_digest: NonEmptyStr
    bundle_digest: NonEmptyStr
    evidence_set_digest: NonEmptyStr
    decision: GovernanceDecisionOutcome
    actor: NonEmptyStr
    actor_authority_type: AuthorizationClass
    workspace_id: NonEmptyStr
    session_id: str | None = None
    purpose: NonEmptyStr
    operation_type: NonEmptyStr
    decision_timestamp: datetime
    reason: str | None = None
    decision_fingerprint: NonEmptyStr
    consumed: bool = False
    consumed_at: datetime | None = None
    consumed_by: str | None = None
