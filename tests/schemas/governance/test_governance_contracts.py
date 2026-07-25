"""Schema contracts and validation tests for governance package."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from schemas.enums import AuthorizationClass, UserDecisionType
from schemas.governance import (
    AuthenticatedPrincipal,
    GovernanceAuthority,
    UserDecision,
)


def test_governance_authority_and_principal_immutability() -> None:
    now = datetime.now(UTC)
    principal = AuthenticatedPrincipal(
        authentication_context_id="ctx-1",
        principal_id="p-1",
        workspace_id="ws-1",
        session_id="sess-1",
        authenticated_at=now,
    )
    authority = GovernanceAuthority(
        authority_id=UUID("00000000-0000-0000-0000-000000000001"),
        actor_identity="p-1",
        authority_class=AuthorizationClass.USER_GOVERNED,
        workspace_id="ws-1",
        session_id="sess-1",
        purpose="evaluation",
        operation_type="approve",
        issued_by="system",
        issued_at=now,
        expires_at=now,
        authority_fingerprint="fp-1",
    )

    with pytest.raises(ValidationError, match="Instance is frozen"):
        principal.principal_id = "p-2"  # type: ignore[misc]

    with pytest.raises(ValidationError, match="Instance is frozen"):
        authority.authority_class = AuthorizationClass.TRUSTED_INTERNAL  # type: ignore[misc]


def test_user_decision_schema_defaults() -> None:
    ud = UserDecision(
        decision_type=UserDecisionType.DATA_SELECTION,
        decision="Selected dataset v1",
        rationale="Primary input dataset",
    )
    assert ud.status.value == "active"
    assert ud.alternatives_considered == []
    assert ud.related_task_ids == []
    assert ud.related_hypothesis_ids == []
