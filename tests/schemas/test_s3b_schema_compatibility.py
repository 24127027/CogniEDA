"""S3-B canonical-owner, enum identity, and serialization compatibility checks."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from schemas import enums
from schemas.governance import (
    AuthenticatedPrincipal,
    GovernanceAuthority,
    GovernanceDecision,
)
from schemas.validity import (
    ValidityPropagationCommand,
)


def test_bounded_packages_reuse_single_canonical_enum_definitions() -> None:
    """Evaluation, governance, discovery, and validity must reuse canonical enum class objects."""

    import schemas.discovery as discovery_pkg
    import schemas.evaluation as evaluation_pkg
    import schemas.governance as governance_pkg
    import schemas.validity as validity_pkg

    evaluation_enums = {"EvaluationControlState"}
    governance_enums = {
        "AuthorizationClass",
        "GovernanceDecisionOutcome",
        "UserDecisionStatus",
        "UserDecisionType",
    }
    discovery_enums = {
        "AnalysisIntent",
        "DiscoveryEpistemicStatus",
        "DiscoveryLifecycleState",
        "DiscoveryAdmissionClaimState",
        "DiscoveryAdmissionReplayDisposition",
    }
    validity_enums = {
        "ValiditySourceType",
        "ValiditySourceState",
        "ValidityEventType",
    }

    for pkg, enum_names in (
        (evaluation_pkg, evaluation_enums),
        (governance_pkg, governance_enums),
        (discovery_pkg, discovery_enums),
        (validity_pkg, validity_enums),
    ):
        for name in enum_names:
            if hasattr(pkg, name):
                assert getattr(pkg, name) is getattr(enums, name)


def test_s3b_models_model_dump_json_is_baseline_compatible() -> None:
    """S3-B schemas dump JSON with exact expected field names and enum values."""

    now = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)

    # Governance Authority & Decision
    principal = AuthenticatedPrincipal(
        authentication_context_id="auth-1",
        principal_id="user-1",
        workspace_id="ws-1",
        session_id="sess-1",
        authenticated_at=now,
    )
    authority = GovernanceAuthority(
        authority_id=UUID("00000000-0000-0000-0000-000000000010"),
        actor_identity="user-1",
        authority_class=enums.AuthorizationClass.USER_GOVERNED,
        workspace_id="ws-1",
        session_id="sess-1",
        purpose="evaluation",
        operation_type="approve_proposal",
        issued_by="system",
        issued_at=now,
        expires_at=now,
        authority_fingerprint="fp-auth-1",
    )
    decision = GovernanceDecision(
        decision_id=UUID("00000000-0000-0000-0000-000000000011"),
        authority_id=authority.authority_id,
        evaluation_id=UUID("00000000-0000-0000-0000-000000000012"),
        evaluation_key="eval-key-1",
        hypothesis_id=UUID("00000000-0000-0000-0000-000000000013"),
        task_id=UUID("00000000-0000-0000-0000-000000000014"),
        proposal_digest="prop-digest-1",
        bundle_digest="bundle-digest-1",
        evidence_set_digest="ev-digest-1",
        decision=enums.GovernanceDecisionOutcome.APPROVED,
        actor="user-1",
        actor_authority_type=enums.AuthorizationClass.USER_GOVERNED,
        workspace_id="ws-1",
        session_id="sess-1",
        purpose="evaluation",
        operation_type="approve_proposal",
        decision_timestamp=now,
        reason="Approved by analyst.",
        decision_fingerprint="fp-dec-1",
    )

    # Validity Command
    validity_cmd = ValidityPropagationCommand(
        source_type=enums.ValiditySourceType.EVIDENCE,
        source_id=UUID("00000000-0000-0000-0000-000000000015"),
        event_type=enums.ValidityEventType.EVIDENCE_INVALIDATION,
        reason="Corrupted observation source.",
        authority_id=authority.authority_id,
        workspace_id="ws-1",
        session_id="sess-1",
        expected_source_state="active",
        expected_source_fingerprint="fp-src-1",
        idempotency_key="idempotency-1",
    )

    assert principal.model_dump(mode="json")["principal_id"] == "user-1"
    assert authority.model_dump(mode="json")["authority_class"] == "user_governed"
    assert decision.model_dump(mode="json")["decision"] == "approved"
    assert validity_cmd.model_dump(mode="json")["source_type"] == "evidence"
    assert validity_cmd.model_dump(mode="json")["event_type"] == "evidence_invalidation"


def test_s3b_schemas_preserve_extra_forbid_and_immutability() -> None:
    """Validation rejects extra input fields and respects frozen model immutability."""

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        AuthenticatedPrincipal(
            authentication_context_id="auth-1",
            principal_id="user-1",
            workspace_id="ws-1",
            session_id="sess-1",
            authenticated_at=datetime.now(UTC),
            unexpected_field="extra",
        )

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ValidityPropagationCommand(
            source_type=enums.ValiditySourceType.EVIDENCE,
            source_id=UUID("00000000-0000-0000-0000-000000000015"),
            event_type=enums.ValidityEventType.EVIDENCE_INVALIDATION,
            reason="Corrupted observation source.",
            authority_id=UUID("00000000-0000-0000-0000-000000000010"),
            workspace_id="ws-1",
            expected_source_state="active",
            expected_source_fingerprint="fp-src-1",
            idempotency_key="idempotency-1",
            extra_arg="rejected",
        )
