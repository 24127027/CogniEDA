"""S3-B canonical-owner, enum identity, and serialization compatibility checks."""

from __future__ import annotations

import hashlib
import inspect
import json
from datetime import UTC, datetime
from enum import Enum
from uuid import UUID

import pytest
from pydantic import BaseModel, ValidationError

from schemas import (
    discovery as discovery_pkg,
)
from schemas import (
    enums,
)
from schemas import (
    evaluation as evaluation_pkg,
)
from schemas import (
    governance as governance_pkg,
)
from schemas import (
    validity as validity_pkg,
)
from schemas.governance import (
    AuthenticatedPrincipal,
    GovernanceAuthority,
    GovernanceDecision,
)
from schemas.validity import (
    ValidityPropagationCommand,
)

S3A_SCHEMA_SNAPSHOT_SHA256 = (
    "0408a3ceb27a6cbc86c2cdfe96fc531cf25ec42ed45c4e5f05d10d7a3ec7e404"
)


def test_bounded_packages_reuse_single_canonical_enum_definitions() -> None:
    """Evaluation, governance, discovery, and validity must reuse canonical enum class objects."""

    import schemas.discovery.admission as discovery_admission
    import schemas.discovery.claim as discovery_claim
    import schemas.evaluation.results as evaluation_results
    import schemas.evaluation.snapshots as evaluation_snapshots
    import schemas.governance.authority as governance_authority
    import schemas.governance.decision as governance_decision
    import schemas.governance.user_decision as governance_user_decision
    import schemas.validity.propagation as validity_propagation

    expected_identities = {
        evaluation_snapshots: ("AnalysisIntent", "DatasetSourceType", "EvidenceType"),
        evaluation_results: ("DiscoveryEpistemicStatus",),
        governance_authority: ("AuthorizationClass",),
        governance_decision: ("AuthorizationClass", "GovernanceDecisionOutcome"),
        governance_user_decision: ("UserDecisionStatus", "UserDecisionType"),
        discovery_claim: (
            "AnalysisIntent",
            "DiscoveryEpistemicStatus",
            "DiscoveryLifecycleState",
        ),
        discovery_admission: (
            "AuthorizationClass",
            "DiscoveryAdmissionReplayDisposition",
            "DiscoveryEpistemicStatus",
            "EvaluationControlState",
            "HypothesisStatus",
            "TaskLifecycleState",
        ),
        validity_propagation: (
            "AuthorizationClass",
            "ValidityEventType",
            "ValiditySourceType",
        ),
    }
    for module, enum_names in expected_identities.items():
        for name in enum_names:
            assert getattr(module, name) is getattr(enums, name)

    exported_enum_owners = {
        value: value.__module__
        for package in (
            evaluation_pkg,
            governance_pkg,
            discovery_pkg,
            validity_pkg,
        )
        for name in package.__all__
        if inspect.isclass(value := getattr(package, name))
        and issubclass(value, Enum)
    }
    assert exported_enum_owners == {
        evaluation_pkg.ActiveStateProof: "schemas.evaluation.bundle",
        evaluation_pkg.EvaluationFailureReason: "schemas.evaluation.results",
        evaluation_pkg.InclusionRole: "schemas.evaluation.bundle",
        evaluation_pkg.ManifestObjectType: "schemas.evaluation.bundle",
        evaluation_pkg.RepositorySource: "schemas.evaluation.bundle",
    }


def test_all_exported_s3b_model_schemas_and_configs_match_s3a() -> None:
    """Hash every exported Pydantic schema/config/field order against S3-A."""

    snapshot = {}
    for package in (
        evaluation_pkg,
        governance_pkg,
        discovery_pkg,
        validity_pkg,
    ):
        package_snapshot = {}
        for name in package.__all__:
            value = getattr(package, name)
            if inspect.isclass(value) and issubclass(value, BaseModel):
                package_snapshot[name] = {
                    "schema": value.model_json_schema(),
                    "config": dict(value.model_config),
                    "fields": list(value.model_fields),
                }
        snapshot[package.__name__] = package_snapshot
    encoded = json.dumps(
        snapshot,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode()
    assert hashlib.sha256(encoded).hexdigest() == S3A_SCHEMA_SNAPSHOT_SHA256


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
