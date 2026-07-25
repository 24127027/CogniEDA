"""Governance authority value objects and principal binding values."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from schemas.common import ImmutableCogniEDABaseModel, NonEmptyStr
from schemas.enums import AuthorizationClass


class AuthenticatedPrincipal(ImmutableCogniEDABaseModel):
    """Authenticated identity provided by an authentication subsystem."""

    authentication_context_id: NonEmptyStr
    principal_id: NonEmptyStr
    workspace_id: NonEmptyStr
    session_id: NonEmptyStr
    authenticated_at: datetime


class GovernanceAuthority(ImmutableCogniEDABaseModel):
    """Durable, independently issued actor authority used to record one decision."""

    authority_id: UUID
    actor_identity: NonEmptyStr
    authority_class: AuthorizationClass
    workspace_id: NonEmptyStr
    session_id: str | None = None
    purpose: NonEmptyStr
    operation_type: NonEmptyStr
    issued_by: NonEmptyStr
    issued_at: datetime
    expires_at: datetime
    authority_fingerprint: NonEmptyStr


class ProposalAuthority(ImmutableCogniEDABaseModel):
    """Immutable identity and provenance binding for a persisted evaluation proposal."""

    evaluation_id: UUID
    evaluation_key: NonEmptyStr
    hypothesis_id: UUID
    source_task_id: UUID
    profile_id: UUID
    proposal_digest: NonEmptyStr
    bundle_digest: NonEmptyStr
    evidence_set_digest: NonEmptyStr
    manifest_digest: NonEmptyStr
    exact_evidence_ids: tuple[UUID, ...]
    exact_analysis_frame_ids: tuple[UUID, ...]
    proposal_contract_version: Literal["1.0"] = "1.0"
    serialized_proposal_identity: NonEmptyStr
    evaluation_attempt_number: int = Field(ge=1)
    evaluation_owner: NonEmptyStr
    evaluation_fencing_epoch: int = Field(ge=1)
    evaluation_created_at: datetime
