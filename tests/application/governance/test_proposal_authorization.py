"""Repository-backed proposal and actor-authorization tests for Package 3."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, update

from application.discovery import build_discovery_admission_plan
from application.evaluation import EvaluationTransitionService, build_synthesis_bundle
from application.governance import (
    DiscoveryAdmissionGovernanceService,
    ProposalAuthorizationError,
)
from db.models import (
    DiscoveryRecord,
    EvaluationControlRecord,
    EvidenceRecord,
    GovernanceAuthorityRecord,
    HypothesisRecord,
    TaskRecord,
)
from package2_helpers import (
    Package2Lineage,
    persist_governance_authority,
    persist_package2_lineage,
    proposal_for_bundle,
)
from schemas.enums import (
    AuthorizationClass,
    DiscoveryEpistemicStatus,
    EvaluationControlState,
    EvidenceLifecycleState,
    GovernanceDecisionOutcome,
    HypothesisStatus,
    TaskLifecycleState,
)


def _setup_proposal_ready_evaluation(
    session: Session,
    *,
    epistemic_status: DiscoveryEpistemicStatus = DiscoveryEpistemicStatus.SUPPORTED,
) -> tuple[
    EvaluationControlRecord,
    DiscoveryAdmissionGovernanceService,
    GovernanceAuthorityRecord,
    Package2Lineage,
]:
    lineage = persist_package2_lineage(session)
    evaluation_service = EvaluationTransitionService(session)
    control_record, _ = evaluation_service.enqueue_evaluation(hypothesis_id=lineage.hypothesis_id)
    claimed = evaluation_service.claim_evaluation(
        evaluation_id=control_record.evaluation_id,
        owner="system:evaluator",
    )
    bundle, _ = build_synthesis_bundle(session, lineage.hypothesis_id)
    proposal = proposal_for_bundle(bundle, epistemic_status=epistemic_status)
    published = evaluation_service.publish_proposal(
        evaluation_id=claimed.evaluation_id,
        owner="system:evaluator",
        fencing_epoch=claimed.fencing_epoch,
        source_bundle_digest=bundle.input_digest,
        proposal=proposal,
    )
    authority = persist_governance_authority(session)
    governance = DiscoveryAdmissionGovernanceService(
        session,
        workspace_id="workspace:test",
        session_id="session:test",
        principal_id="user:lead_researcher",
    )
    return published, governance, authority, lineage


def _record_decision(
    governance: DiscoveryAdmissionGovernanceService,
    published: EvaluationControlRecord,
    authority: GovernanceAuthorityRecord,
    *,
    decision: GovernanceDecisionOutcome = GovernanceDecisionOutcome.APPROVED,
):
    return governance.record_governance_decision(
        evaluation_id=published.evaluation_id,
        authority_id=authority.authority_id,
        decision=decision,
    )


def test_exact_persisted_proposal_and_durable_actor_authority_are_approved(
    db_session: Session,
) -> None:
    published, governance, authority, _ = _setup_proposal_ready_evaluation(db_session)
    decision = _record_decision(
        governance,
        published,
        authority,
    )

    proposal_authority, verified = governance.verify_authorization(
        published.evaluation_id,
        decision.decision_id,
    )

    assert proposal_authority.proposal_digest == published.proposal_digest
    assert proposal_authority.bundle_digest == published.bundle_digest
    assert proposal_authority.evidence_set_digest == published.evidence_set_digest
    assert proposal_authority.evaluation_key == published.evaluation_key
    assert verified.authority_id == authority.authority_id
    assert verified.workspace_id == "workspace:test"
    assert verified.session_id == "session:test"
    assert verified.consumed is False


@pytest.mark.parametrize(
    "outcome",
    [GovernanceDecisionOutcome.REJECTED, GovernanceDecisionOutcome.CANCELLED],
)
def test_non_approved_decision_cannot_create_plan(
    db_session: Session,
    outcome: GovernanceDecisionOutcome,
) -> None:
    published, governance, authority, lineage = _setup_proposal_ready_evaluation(db_session)
    decision = _record_decision(governance, published, authority, decision=outcome)

    with pytest.raises(ProposalAuthorizationError, match="must be APPROVED"):
        build_discovery_admission_plan(
            db_session,
            published.evaluation_id,
            decision.decision_id,
            workspace_id="workspace:test",
            session_id="session:test",
        )

    hypothesis = db_session.get(HypothesisRecord, lineage.hypothesis_id)
    task = db_session.get(TaskRecord, lineage.task_id)
    assert hypothesis is not None
    assert hypothesis.status == HypothesisStatus.READY_FOR_EVALUATION
    assert task is not None and task.lifecycle_state == TaskLifecycleState.ACTIVE


def test_missing_or_inactive_authority_cannot_be_self_declared(db_session: Session) -> None:
    published, governance, _, _ = _setup_proposal_ready_evaluation(db_session)
    with pytest.raises(ProposalAuthorizationError, match="authority record not found"):
        governance.record_governance_decision(
            evaluation_id=published.evaluation_id,
            authority_id=uuid4(),
            decision=GovernanceDecisionOutcome.APPROVED,
        )

    inactive = persist_governance_authority(db_session, active=False)
    with pytest.raises(ProposalAuthorizationError, match="inactive or expired"):
        governance.record_governance_decision(
            evaluation_id=published.evaluation_id,
            authority_id=inactive.authority_id,
            decision=GovernanceDecisionOutcome.APPROVED,
        )


def test_wrong_authenticated_principal_cannot_use_another_users_authority(
    db_session: Session,
) -> None:
    published, _, authority, _ = _setup_proposal_ready_evaluation(db_session)
    wrong_principal = DiscoveryAdmissionGovernanceService(
        db_session,
        workspace_id="workspace:test",
        session_id="session:test",
        principal_id="user:other_researcher",
    )

    with pytest.raises(ProposalAuthorizationError, match="does not own"):
        wrong_principal.record_governance_decision(
            evaluation_id=published.evaluation_id,
            authority_id=authority.authority_id,
            decision=GovernanceDecisionOutcome.APPROVED,
        )


def test_user_governed_decision_requires_explicit_authenticated_principal(
    db_session: Session,
) -> None:
    published, _, authority, _ = _setup_proposal_ready_evaluation(db_session)
    unbound = DiscoveryAdmissionGovernanceService(
        db_session,
        workspace_id="workspace:test",
        session_id="session:test",
    )

    with pytest.raises(ProposalAuthorizationError, match="authenticated principal"):
        unbound.record_governance_decision(
            evaluation_id=published.evaluation_id,
            authority_id=authority.authority_id,
            decision=GovernanceDecisionOutcome.APPROVED,
        )


def test_spoofed_trusted_internal_authority_is_rejected(db_session: Session) -> None:
    published, _, _, _ = _setup_proposal_ready_evaluation(db_session)
    spoofed = persist_governance_authority(
        db_session,
        authority_class=AuthorizationClass.TRUSTED_INTERNAL,
        actor_identity="spoofed:admin",
    )
    governance = DiscoveryAdmissionGovernanceService(
        db_session,
        workspace_id="workspace:test",
    )
    with pytest.raises(ProposalAuthorizationError, match="durably allow-listed"):
        governance.record_governance_decision(
            evaluation_id=published.evaluation_id,
            authority_id=spoofed.authority_id,
            decision=GovernanceDecisionOutcome.APPROVED,
        )


def test_allowlisted_trusted_internal_requires_durable_purpose_and_operation(
    db_session: Session,
) -> None:
    published, _, _, _ = _setup_proposal_ready_evaluation(db_session)
    trusted = persist_governance_authority(
        db_session,
        authority_class=AuthorizationClass.TRUSTED_INTERNAL,
        actor_identity="system:internal_batch",
        purpose="automated_batch_admission",
        operation_type="authorize_proposal",
    )
    governance = DiscoveryAdmissionGovernanceService(
        db_session,
        workspace_id="workspace:test",
    )
    decision = governance.record_governance_decision(
        evaluation_id=published.evaluation_id,
        authority_id=trusted.authority_id,
        decision=GovernanceDecisionOutcome.APPROVED,
    )
    assert decision.authority_id == trusted.authority_id
    assert decision.purpose == "automated_batch_admission"
    assert decision.operation_type == "authorize_proposal"


def test_cross_session_and_cross_workspace_replay_are_rejected(db_session: Session) -> None:
    published, governance, authority, _ = _setup_proposal_ready_evaluation(db_session)
    decision = _record_decision(governance, published, authority)

    wrong_session = DiscoveryAdmissionGovernanceService(
        db_session,
        workspace_id="workspace:test",
        session_id="session:other",
    )
    with pytest.raises(ProposalAuthorizationError, match="session and operation"):
        wrong_session.verify_authorization(published.evaluation_id, decision.decision_id)

    wrong_workspace = DiscoveryAdmissionGovernanceService(
        db_session,
        workspace_id="workspace:other",
        session_id="session:test",
    )
    with pytest.raises(ProposalAuthorizationError, match="workspace mismatch"):
        wrong_workspace.verify_authorization(published.evaluation_id, decision.decision_id)


def test_decision_for_another_evaluation_cannot_authorize(db_session: Session) -> None:
    first, governance, authority, _ = _setup_proposal_ready_evaluation(db_session)
    second, _, _, _ = _setup_proposal_ready_evaluation(db_session)
    decision = _record_decision(governance, first, authority)

    with pytest.raises(ProposalAuthorizationError, match="evaluation_id mismatch"):
        governance.verify_authorization(second.evaluation_id, decision.decision_id)


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("proposal_digest", "tampered-proposal", "proposal digest"),
        ("bundle_digest", "tampered-bundle", "canonical protected bundle"),
        ("evidence_set_digest", "tampered-evidence-set", "canonical protected bundle"),
        ("evaluation_key", "tampered-evaluation", "canonical protected bundle"),
    ],
)
def test_modified_persisted_evaluation_identity_is_rejected(
    db_session: Session,
    column: str,
    value: str,
    message: str,
) -> None:
    published, governance, authority, _ = _setup_proposal_ready_evaluation(db_session)
    decision = _record_decision(governance, published, authority)
    db_session.execute(
        update(EvaluationControlRecord)
        .where(EvaluationControlRecord.evaluation_id == published.evaluation_id)
        .values(**{column: value})
    )
    db_session.commit()

    with pytest.raises(ProposalAuthorizationError, match=message):
        governance.verify_authorization(published.evaluation_id, decision.decision_id)


@pytest.mark.parametrize(
    "stale_lifecycle",
    [EvidenceLifecycleState.INVALIDATED, EvidenceLifecycleState.SUPERSEDED],
)
def test_stale_evidence_or_cancelled_evaluation_invalidates_authority(
    db_session: Session,
    stale_lifecycle: EvidenceLifecycleState,
) -> None:
    published, governance, authority, _ = _setup_proposal_ready_evaluation(db_session)
    decision = _record_decision(governance, published, authority)
    evidence_id = UUID(str(published.evidence_ids[0]))
    evidence = db_session.get(EvidenceRecord, evidence_id)
    assert evidence is not None
    evidence.lifecycle_state = stale_lifecycle
    if stale_lifecycle == EvidenceLifecycleState.SUPERSEDED:
        replacement = EvidenceRecord(
            evidence_id=uuid4(),
            hypothesis_id=evidence.hypothesis_id,
            profile_id=evidence.profile_id,
            analysis_frame_ref=evidence.analysis_frame_ref,
            execution_run_ref=evidence.execution_run_ref,
            evidence_type=evidence.evidence_type,
            method=evidence.method,
            parameters=evidence.parameters,
            provenance=evidence.provenance,
            result_summary=evidence.result_summary,
            artifact_refs=evidence.artifact_refs,
            limitations=evidence.limitations,
        )
        db_session.add(replacement)
        db_session.flush()
        evidence.superseded_by_evidence_id = replacement.evidence_id
    db_session.add(evidence)
    db_session.commit()
    with pytest.raises(ProposalAuthorizationError, match="stale or invalid"):
        governance.verify_authorization(published.evaluation_id, decision.decision_id)

    evidence.lifecycle_state = EvidenceLifecycleState.ACTIVE
    evidence.superseded_by_evidence_id = None
    db_session.add(evidence)
    control = db_session.get(EvaluationControlRecord, published.evaluation_id)
    assert control is not None
    control.state = EvaluationControlState.CANCELLED
    db_session.add(control)
    db_session.commit()
    with pytest.raises(ProposalAuthorizationError, match="must be PROPOSAL_READY"):
        governance.verify_authorization(published.evaluation_id, decision.decision_id)


def test_existing_discovery_blocks_authorization_without_overwrite(db_session: Session) -> None:
    published, governance, authority, _ = _setup_proposal_ready_evaluation(db_session)
    decision = _record_decision(governance, published, authority)
    db_session.add(
        DiscoveryRecord(
            hypothesis_id=published.hypothesis_id,
            evidence_ids=published.evidence_ids,
            claim={"statement": "Pre-existing claim"},
            epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
            scope="Global",
            validity_basis={},
            invalidators=[],
        )
    )
    db_session.commit()

    with pytest.raises(ProposalAuthorizationError, match="Discovery"):
        governance.verify_authorization(published.evaluation_id, decision.decision_id)


def test_plan_construction_rejects_dirty_session_without_flushing(db_session: Session) -> None:
    published, governance, authority, _ = _setup_proposal_ready_evaluation(db_session)
    decision = _record_decision(governance, published, authority)
    transient = TaskRecord(
        title="Unrelated pending caller change",
        description="Must not be flushed by read-only plan construction.",
    )
    evaluation_id = published.evaluation_id
    decision_id = decision.decision_id
    db_session.add(transient)

    with pytest.raises(ProposalAuthorizationError, match="clean session"):
        build_discovery_admission_plan(
            db_session,
            evaluation_id,
            decision_id,
            workspace_id="workspace:test",
            session_id="session:test",
        )
    assert transient in db_session.new
    db_session.rollback()


def test_database_rejects_unauthorized_authority_class(db_session: Session) -> None:
    with pytest.raises(IntegrityError):
        persist_governance_authority(
            db_session,
            authority_class=AuthorizationClass.UNAUTHORIZED,
        )
    db_session.rollback()
