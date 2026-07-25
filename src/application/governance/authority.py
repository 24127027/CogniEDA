"""Authenticated principal resolver protocol and authority issuer service."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from sqlmodel import Session

from application.governance.fingerprints import (
    _datetime_is_expired,
    compute_governance_authority_fingerprint,
)
from db.models import GovernanceAuthorityRecord, utc_now
from schemas.enums import AuthorizationClass
from schemas.governance import AuthenticatedPrincipal

USER_GOVERNED_PURPOSE = "governed_discovery_admission"
USER_GOVERNED_OPERATION_TYPE = "authorize_proposal"
GOVERNANCE_AUTHORITY_ISSUER_ID = "service:governance_authority_issuer"


class ProposalAuthorizationError(ValueError):
    """Raised when proposal authority or authorization verification fails."""


class AuthenticatedPrincipalResolver(Protocol):
    """Trusted authentication adapter supplied by the production composition root."""

    def resolve_authenticated_principal(
        self,
        authentication_context_id: str,
    ) -> AuthenticatedPrincipal:
        """Resolve one server-authenticated principal; never accept caller identity fields."""


class GovernanceAuthorityIssuer:
    """Production authority issuer boundary for user-governed decision authority."""

    def __init__(
        self,
        session: Session,
        *,
        principal_resolver: AuthenticatedPrincipalResolver,
        workspace_id: str,
        session_id: str | None = None,
    ) -> None:
        if not workspace_id.strip():
            raise ValueError("Governance authority issuer requires a non-empty workspace identity.")
        if session_id is not None and not session_id.strip():
            raise ValueError("Session identity must be non-empty when supplied.")
        self._session = session
        self._principal_resolver = principal_resolver
        self._workspace_id = workspace_id
        self._session_id = session_id

    def issue_user_authority(
        self,
        *,
        authentication_context_id: str,
        expires_at: datetime | None = None,
    ) -> GovernanceAuthorityRecord:
        """Resolve authenticated identity and durably issue one fixed-purpose grant."""

        if self._session.new or self._session.dirty or self._session.deleted:
            raise ProposalAuthorizationError("Authority issuer requires a clean unit of work.")

        if not authentication_context_id.strip():
            raise ProposalAuthorizationError("Authentication context identity cannot be empty.")
        principal = self._principal_resolver.resolve_authenticated_principal(
            authentication_context_id
        )
        if principal.authentication_context_id != authentication_context_id:
            raise ProposalAuthorizationError("Authentication context identity mismatch.")
        if principal.workspace_id != self._workspace_id:
            raise ProposalAuthorizationError("Authenticated principal workspace mismatch.")
        if self._session_id is None or principal.session_id != self._session_id:
            raise ProposalAuthorizationError("Authenticated principal session mismatch.")

        now = utc_now()
        authenticated_at = principal.authenticated_at
        if authenticated_at.tzinfo is None:
            authenticated_at = authenticated_at.replace(tzinfo=UTC)
        if authenticated_at > now:
            raise ProposalAuthorizationError("Authenticated principal timestamp is in the future.")
        if _datetime_is_expired(expires_at, now):
            raise ProposalAuthorizationError("Cannot issue an already-expired authority grant.")

        authority_id = uuid4()
        fingerprint = compute_governance_authority_fingerprint(
            authority_id=authority_id,
            actor_identity=principal.principal_id,
            authority_class=AuthorizationClass.USER_GOVERNED,
            workspace_id=self._workspace_id,
            session_id=self._session_id,
            purpose=USER_GOVERNED_PURPOSE,
            operation_type=USER_GOVERNED_OPERATION_TYPE,
            issued_by=GOVERNANCE_AUTHORITY_ISSUER_ID,
            issued_at=now,
            expires_at=expires_at,
        )

        record = GovernanceAuthorityRecord(
            authority_id=authority_id,
            actor_identity=principal.principal_id,
            authority_class=AuthorizationClass.USER_GOVERNED,
            workspace_id=self._workspace_id,
            session_id=self._session_id,
            purpose=USER_GOVERNED_PURPOSE,
            operation_type=USER_GOVERNED_OPERATION_TYPE,
            issued_by=GOVERNANCE_AUTHORITY_ISSUER_ID,
            issued_at=now,
            expires_at=expires_at,
            active=True,
            authority_fingerprint=fingerprint,
        )

        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record
