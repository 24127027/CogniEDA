"""Comprehensive Package 5 test suite for Atomic Discovery Authority Cutover."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from threading import Barrier, Event
from uuid import uuid4

import pytest
from sqlalchemy import inspect as inspect_database
from sqlalchemy import text, update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from application.evaluation import EvaluationTransitionService, build_synthesis_bundle
from application.governance import (
    DiscoveryAdmissionGovernanceService,
    GovernanceAuthorityIssuer,
    ProposalAuthorizationError,
    ProposalDecisionConflictError,
)
from application.orchestrator.atomic_discovery_admission import (
    AtomicDiscoveryAdmissionConflictError,
    AtomicDiscoveryAdmissionError,
    AtomicDiscoveryAdmissionService,
)
from application.orchestrator.discovery_admission_coordinator import DiscoveryAdmissionCoordinator
from db.init_db import init_db
from db.models import (
    DiscoveryAdmissionClaimRecord,
    DiscoveryRecord,
    EvaluationControlRecord,
    HypothesisRecord,
    ProposalDecisionRecord,
    SessionFrameRecord,
    TaskRecord,
    utc_now,
)
from db.session import get_session
from package2_helpers import (
    Package2Lineage,
    persist_package2_lineage,
    propagate_validity_for_test,
    proposal_for_bundle,
)
from repositories.discovery_repository import DiscoveryRepository
from repositories.evidence_repository import EvidenceRepository
from repositories.objective_repository import ObjectiveRepository
from repositories.task_repository import TaskRepository
from schemas.artifacts import Objective, Task
from schemas.enums import (
    AuthorizationClass,
    DiscoveryAdmissionClaimState,
    DiscoveryAdmissionReplayDisposition,
    DiscoveryEpistemicStatus,
    DiscoveryLifecycleState,
    EvaluationControlState,
    GovernanceDecisionOutcome,
    HypothesisStatus,
    TaskKind,
    TaskLifecycleState,
    ValidityEventType,
    ValiditySourceType,
)
from schemas.evaluation import DiscoveryProposal
from schemas.governance import AuthenticatedPrincipal


class _StaticPrincipalResolver:
    def __init__(self, principal: AuthenticatedPrincipal) -> None:
        self._principal = principal

    def resolve_authenticated_principal(
        self, authentication_context_id: str
    ) -> AuthenticatedPrincipal:
        return self._principal


def _principal(
    *,
    workspace_id: str = "ws:1",
    session_id: str = "sess:1",
) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        authentication_context_id="authctx:1",
        principal_id="user:alice",
        workspace_id=workspace_id,
        session_id=session_id,
        authenticated_at=utc_now(),
    )


def _issuer(
    session: Session,
    principal: AuthenticatedPrincipal,
) -> GovernanceAuthorityIssuer:
    return GovernanceAuthorityIssuer(
        session,
        principal_resolver=_StaticPrincipalResolver(principal),
        workspace_id="ws:1",
        session_id="sess:1",
    )


def _issue_admission_authority(
    session: Session,
    *,
    workspace_id: str = "workspace:test",
    session_id: str = "session:test",
):
    principal = _principal(workspace_id=workspace_id, session_id=session_id)
    issuer = GovernanceAuthorityIssuer(
        session,
        principal_resolver=_StaticPrincipalResolver(principal),
        workspace_id=workspace_id,
        session_id=session_id,
    )
    return issuer.issue_user_authority(
        authentication_context_id=principal.authentication_context_id,
        expires_at=utc_now() + timedelta(hours=1),
    )


@pytest.fixture
def test_db_engine(tmp_path: Path):
    db_file = tmp_path / "test_package5.db"
    db_url = f"sqlite:///{db_file}"
    init_db(db_url)
    from db.session import create_db_engine

    return create_db_engine(db_url)


def _setup_package2_ready_evaluation(
    session: Session,
    *,
    p_value: float = 0.01,
    epistemic_status: DiscoveryEpistemicStatus = DiscoveryEpistemicStatus.SUPPORTED,
) -> tuple[Package2Lineage, EvaluationControlRecord, DiscoveryProposal]:
    """Helper to stage line items up to PROPOSAL_READY state."""

    ObjectiveRepository(session).create_for_bootstrap(
        Objective(
            title="Package 5 objective",
            statement="Admit the evaluated analytical conclusion.",
        )
    )
    lineage = persist_package2_lineage(session, p_value=p_value)
    bundle, _ = build_synthesis_bundle(session, lineage.hypothesis_id)
    eval_service = EvaluationTransitionService(session)

    eval_control, _ = eval_service.enqueue_evaluation(hypothesis_id=lineage.hypothesis_id)
    eval_control = eval_service.claim_evaluation(
        evaluation_id=eval_control.evaluation_id, owner="evaluator:test"
    )

    proposal = proposal_for_bundle(bundle, epistemic_status=epistemic_status)
    eval_service.publish_proposal(
        evaluation_id=eval_control.evaluation_id,
        owner="evaluator:test",
        fencing_epoch=eval_control.fencing_epoch,
        source_bundle_digest=eval_control.bundle_digest,
        proposal=proposal,
    )

    session.refresh(eval_control)
    return lineage, eval_control, proposal


def _setup_authorized_admission(
    session: Session,
    *,
    epistemic_status: DiscoveryEpistemicStatus = DiscoveryEpistemicStatus.SUPPORTED,
) -> tuple[
    Package2Lineage,
    EvaluationControlRecord,
    DiscoveryProposal,
    ProposalDecisionRecord,
]:
    lineage, evaluation, proposal = _setup_package2_ready_evaluation(
        session,
        epistemic_status=epistemic_status,
    )
    grant = _issue_admission_authority(session)
    decision = DiscoveryAdmissionGovernanceService(
        session,
        workspace_id="workspace:test",
        session_id="session:test",
        principal_id="user:alice",
    ).record_governance_decision(
        evaluation_id=evaluation.evaluation_id,
        authority_id=grant.authority_id,
        decision=GovernanceDecisionOutcome.APPROVED,
    )
    return lineage, evaluation, proposal, decision


# ============================================================================
# Section 1: Authority Issuer Tests
# ============================================================================


def test_governance_authority_issuer_user_grant_success(test_db_engine):
    with Session(test_db_engine) as session:
        principal = _principal()
        issuer = _issuer(session, principal)
        grant = issuer.issue_user_authority(
            authentication_context_id=principal.authentication_context_id,
            expires_at=utc_now() + timedelta(hours=1),
        )

        assert grant.authority_id is not None
        assert grant.actor_identity == "user:alice"
        assert grant.authority_class == AuthorizationClass.USER_GOVERNED
        assert grant.workspace_id == "ws:1"
        assert grant.session_id == "sess:1"
        assert grant.active is True
        assert grant.expires_at is not None


def test_governance_authority_issuer_requires_expiry(test_db_engine):
    with Session(test_db_engine) as session:
        principal = _principal()
        issuer = _issuer(session, principal)

        with pytest.raises(ProposalAuthorizationError, match="explicit expiry"):
            issuer.issue_user_authority(
                authentication_context_id=principal.authentication_context_id
            )


def test_governance_authority_issuer_cross_workspace_session_rejected(test_db_engine):
    with Session(test_db_engine) as session:
        principal = _principal(workspace_id="ws:2")
        issuer = _issuer(session, principal)

        with pytest.raises(ProposalAuthorizationError, match="workspace mismatch"):
            issuer.issue_user_authority(
                authentication_context_id=principal.authentication_context_id,
                expires_at=utc_now() + timedelta(hours=1),
            )


def test_governance_authority_issuer_expired_grant_rejected(test_db_engine):
    with Session(test_db_engine) as session:
        principal = _principal()
        issuer = _issuer(session, principal)
        expired_at = utc_now() - timedelta(minutes=10)

        with pytest.raises(ProposalAuthorizationError, match="already-expired"):
            issuer.issue_user_authority(
                authentication_context_id=principal.authentication_context_id,
                expires_at=expired_at,
            )


def test_governance_authority_issuer_rejects_resolver_context_substitution(test_db_engine):
    with Session(test_db_engine) as session:
        principal = _principal()
        substituted = principal.model_copy(update={"authentication_context_id": "authctx:other"})
        issuer = _issuer(session, substituted)

        with pytest.raises(ProposalAuthorizationError, match="context identity mismatch"):
            issuer.issue_user_authority(
                authentication_context_id=principal.authentication_context_id,
                expires_at=utc_now() + timedelta(hours=1),
            )


# ============================================================================
# Section 2: Decision Service Tests
# ============================================================================


def test_record_governance_decision_exact_replay_and_conflict(test_db_engine):
    with Session(test_db_engine) as session:
        _, eval_control, _ = _setup_package2_ready_evaluation(session)
        grant = _issue_admission_authority(session)
        gov_service = DiscoveryAdmissionGovernanceService(
            session,
            workspace_id="workspace:test",
            session_id="session:test",
            principal_id="user:alice",
        )

        dec1 = gov_service.record_governance_decision(
            evaluation_id=eval_control.evaluation_id,
            authority_id=grant.authority_id,
            decision=GovernanceDecisionOutcome.APPROVED,
        )
        assert dec1.decision == GovernanceDecisionOutcome.APPROVED

        # Exact replay
        dec2 = gov_service.record_governance_decision(
            evaluation_id=eval_control.evaluation_id,
            authority_id=grant.authority_id,
            decision=GovernanceDecisionOutcome.APPROVED,
        )
        assert dec2.decision_id == dec1.decision_id

        # Conflict outcome
        with pytest.raises(ProposalDecisionConflictError, match="conflicting decision"):
            gov_service.record_governance_decision(
                evaluation_id=eval_control.evaluation_id,
                authority_id=grant.authority_id,
                decision=GovernanceDecisionOutcome.REJECTED,
            )


# ============================================================================
# Section 3: Claim & Fencing Tests
# ============================================================================


def test_discovery_admission_claim_lifecycle(test_db_engine):
    with Session(test_db_engine) as session:
        _, evaluation, _, decision = _setup_authorized_admission(session)
        service = AtomicDiscoveryAdmissionService(
            session,
            workspace_id="workspace:test",
            session_id="session:test",
        )
        claim = service.enqueue_admission(
            evaluation_id=evaluation.evaluation_id,
            decision_id=decision.decision_id,
        )
        assert claim.state == DiscoveryAdmissionClaimState.PENDING

        lease = service.claim_admission(
            evaluation_id=evaluation.evaluation_id,
            decision_id=decision.decision_id,
            claim_owner="worker:one",
        )
        session.expire_all()
        claimed = session.get(DiscoveryAdmissionClaimRecord, lease.claim_id)
        assert claimed is not None
        assert claimed.state == DiscoveryAdmissionClaimState.CLAIMED
        assert claimed.fencing_epoch == lease.fencing_epoch
        assert claimed.claim_token_digest
        assert claimed.claim_token_digest != lease.claim_token

        with pytest.raises(AtomicDiscoveryAdmissionConflictError):
            service.claim_admission(
                evaluation_id=evaluation.evaluation_id,
                decision_id=decision.decision_id,
                claim_owner="worker:two",
            )


# ============================================================================
# Section 4: Atomic Admission Tests (All Epistemic Statuses)
# ============================================================================


@pytest.mark.parametrize(
    "epistemic_status",
    [
        DiscoveryEpistemicStatus.SUPPORTED,
        DiscoveryEpistemicStatus.CONTRADICTED,
        DiscoveryEpistemicStatus.INCONCLUSIVE,
        DiscoveryEpistemicStatus.INSUFFICIENT_EVIDENCE,
    ],
)
def test_atomic_discovery_admission_all_statuses(test_db_engine, epistemic_status):
    with Session(test_db_engine) as session:
        lineage, eval_control, _ = _setup_package2_ready_evaluation(
            session, epistemic_status=epistemic_status
        )
        grant = _issue_admission_authority(session)
        gov_service = DiscoveryAdmissionGovernanceService(
            session,
            workspace_id="workspace:test",
            session_id="session:test",
            principal_id="user:alice",
        )
        dec = gov_service.record_governance_decision(
            evaluation_id=eval_control.evaluation_id,
            authority_id=grant.authority_id,
            decision=GovernanceDecisionOutcome.APPROVED,
        )

        admission_service = AtomicDiscoveryAdmissionService(
            session, workspace_id="workspace:test", session_id="session:test"
        )
        result = admission_service.execute_admission(
            evaluation_id=eval_control.evaluation_id,
            decision_id=dec.decision_id,
        )

        assert result.disposition == DiscoveryAdmissionReplayDisposition.NEW

        # Verify exact single commit state across all FCOs and records
        discovery = session.get(DiscoveryRecord, result.discovery_id)
        assert discovery is not None
        assert discovery.epistemic_status == epistemic_status
        assert discovery.lifecycle_state == DiscoveryLifecycleState.ACTIVE

        hyp = session.get(HypothesisRecord, lineage.hypothesis_id)
        assert hyp.status == HypothesisStatus.EVALUATED

        task = session.get(TaskRecord, lineage.task_id)
        assert task.lifecycle_state == TaskLifecycleState.COMPLETED

        ctrl = session.get(EvaluationControlRecord, eval_control.evaluation_id)
        assert ctrl.state == EvaluationControlState.COMMITTED

        decision_rec = session.get(ProposalDecisionRecord, dec.decision_id)
        assert decision_rec.consumed is True
        assert decision_rec.consumed_by == str(result.discovery_id)

        claim_rec = session.exec(
            select(DiscoveryAdmissionClaimRecord).where(
                DiscoveryAdmissionClaimRecord.evaluation_id == eval_control.evaluation_id
            )
        ).first()
        assert claim_rec.state == DiscoveryAdmissionClaimState.COMMITTED

        session_frame = session.get(SessionFrameRecord, result.session_frame_id)
        assert session_frame is not None
        assert str(result.discovery_id) in session_frame.relevant_discovery_refs


# ============================================================================
# Section 5: Negative Admission Tests
# ============================================================================


def test_atomic_discovery_admission_negative_rejected_decision(test_db_engine):
    with Session(test_db_engine) as session:
        _, eval_control, _ = _setup_package2_ready_evaluation(session)
        grant = _issue_admission_authority(session)
        gov_service = DiscoveryAdmissionGovernanceService(
            session,
            workspace_id="workspace:test",
            session_id="session:test",
            principal_id="user:alice",
        )
        dec = gov_service.record_governance_decision(
            evaluation_id=eval_control.evaluation_id,
            authority_id=grant.authority_id,
            decision=GovernanceDecisionOutcome.REJECTED,
        )

        admission_service = AtomicDiscoveryAdmissionService(
            session, workspace_id="workspace:test", session_id="session:test"
        )
        with pytest.raises(AtomicDiscoveryAdmissionError, match="APPROVED"):
            admission_service.execute_admission(
                evaluation_id=eval_control.evaluation_id,
                decision_id=dec.decision_id,
            )


def test_atomic_discovery_admission_negative_invalidated_evidence(test_db_engine):
    with Session(test_db_engine) as session:
        lineage, eval_control, _ = _setup_package2_ready_evaluation(session)
        grant = _issue_admission_authority(session)
        gov_service = DiscoveryAdmissionGovernanceService(
            session,
            workspace_id="workspace:test",
            session_id="session:test",
            principal_id="user:alice",
        )
        dec = gov_service.record_governance_decision(
            evaluation_id=eval_control.evaluation_id,
            authority_id=grant.authority_id,
            decision=GovernanceDecisionOutcome.APPROVED,
        )

        # Invalidate evidence via Package 4 validity propagation
        propagate_validity_for_test(
            session,
            source_type=ValiditySourceType.EVIDENCE,
            source_id=lineage.evidence_id,
            event_type=ValidityEventType.EVIDENCE_INVALIDATION,
            reason="Data corrupt",
            idempotency_key="key:invalid_ev_1",
        )

        admission_service = AtomicDiscoveryAdmissionService(
            session, workspace_id="workspace:test", session_id="session:test"
        )
        with pytest.raises(AtomicDiscoveryAdmissionError):
            admission_service.execute_admission(
                evaluation_id=eval_control.evaluation_id,
                decision_id=dec.decision_id,
            )


def test_atomic_discovery_admission_negative_parent_task(test_db_engine):
    with Session(test_db_engine) as session:
        lineage, eval_control, _ = _setup_package2_ready_evaluation(session)
        grant = _issue_admission_authority(session)
        gov_service = DiscoveryAdmissionGovernanceService(
            session,
            workspace_id="workspace:test",
            session_id="session:test",
            principal_id="user:alice",
        )
        dec = gov_service.record_governance_decision(
            evaluation_id=eval_control.evaluation_id,
            authority_id=grant.authority_id,
            decision=GovernanceDecisionOutcome.APPROVED,
        )

        # Add a child task to make the Task non-terminal
        child_task = Task(
            title="Child task",
            description="Child tasks make parent non-terminal",
            parent_task_id=lineage.task_id,
            task_kind=TaskKind.ANALYTICAL,
            lifecycle_state=TaskLifecycleState.ACTIVE,
        )
        TaskRepository(session).create(child_task)

        admission_service = AtomicDiscoveryAdmissionService(
            session, workspace_id="workspace:test", session_id="session:test"
        )
        with pytest.raises(AtomicDiscoveryAdmissionError, match="not a terminal analytical Task"):
            admission_service.execute_admission(
                evaluation_id=eval_control.evaluation_id,
                decision_id=dec.decision_id,
            )


# ============================================================================
# Section 6: Replay & Partial-State Tests
# ============================================================================


def test_atomic_discovery_admission_idempotent_replay(test_db_engine):
    with Session(test_db_engine) as session:
        _, eval_control, _ = _setup_package2_ready_evaluation(session)
        grant = _issue_admission_authority(session)
        gov_service = DiscoveryAdmissionGovernanceService(
            session,
            workspace_id="workspace:test",
            session_id="session:test",
            principal_id="user:alice",
        )
        dec = gov_service.record_governance_decision(
            evaluation_id=eval_control.evaluation_id,
            authority_id=grant.authority_id,
            decision=GovernanceDecisionOutcome.APPROVED,
        )

        admission_service = AtomicDiscoveryAdmissionService(
            session, workspace_id="workspace:test", session_id="session:test"
        )
        res1 = admission_service.execute_admission(
            evaluation_id=eval_control.evaluation_id,
            decision_id=dec.decision_id,
        )
        assert res1.disposition == DiscoveryAdmissionReplayDisposition.NEW

        # Idempotent second call
        res2 = admission_service.execute_admission(
            evaluation_id=eval_control.evaluation_id,
            decision_id=dec.decision_id,
        )
        assert res2.disposition == DiscoveryAdmissionReplayDisposition.IDEMPOTENT
        assert res2.discovery_id == res1.discovery_id


# ============================================================================
# Section 7: Concurrency & Real Overlapping Session Tests
# ============================================================================


def test_atomic_discovery_admission_concurrency_two_workers(test_db_engine):
    session1 = Session(test_db_engine)
    session2 = Session(test_db_engine)
    try:
        _, eval_control, _ = _setup_package2_ready_evaluation(session1)
        grant = _issue_admission_authority(session1)
        gov_service = DiscoveryAdmissionGovernanceService(
            session1,
            workspace_id="workspace:test",
            session_id="session:test",
            principal_id="user:alice",
        )
        dec = gov_service.record_governance_decision(
            evaluation_id=eval_control.evaluation_id,
            authority_id=grant.authority_id,
            decision=GovernanceDecisionOutcome.APPROVED,
        )

        adm1 = AtomicDiscoveryAdmissionService(
            session1, workspace_id="workspace:test", session_id="session:test"
        )
        adm2 = AtomicDiscoveryAdmissionService(
            session2, workspace_id="workspace:test", session_id="session:test"
        )

        res1 = adm1.execute_admission(
            evaluation_id=eval_control.evaluation_id,
            decision_id=dec.decision_id,
            claim_owner="worker_1",
        )
        assert res1.disposition == DiscoveryAdmissionReplayDisposition.NEW

        # Second worker sees existing committed admission
        res2 = adm2.execute_admission(
            evaluation_id=eval_control.evaluation_id,
            decision_id=dec.decision_id,
            claim_owner="worker_2",
        )
        assert res2.disposition == DiscoveryAdmissionReplayDisposition.IDEMPOTENT
        assert res2.discovery_id == res1.discovery_id

    finally:
        session1.close()
        session2.close()


# ============================================================================
# Section 8: Active Retrieval & Retrieval Policy Integration
# ============================================================================


def test_atomic_discovery_retrieval_and_validity_invalidation(test_db_engine):
    with Session(test_db_engine) as session:
        lineage, eval_control, _ = _setup_package2_ready_evaluation(session)
        grant = _issue_admission_authority(session)
        gov_service = DiscoveryAdmissionGovernanceService(
            session,
            workspace_id="workspace:test",
            session_id="session:test",
            principal_id="user:alice",
        )
        dec = gov_service.record_governance_decision(
            evaluation_id=eval_control.evaluation_id,
            authority_id=grant.authority_id,
            decision=GovernanceDecisionOutcome.APPROVED,
        )

        admission_service = AtomicDiscoveryAdmissionService(
            session, workspace_id="workspace:test", session_id="session:test"
        )
        res = admission_service.execute_admission(
            evaluation_id=eval_control.evaluation_id,
            decision_id=dec.decision_id,
        )

        # Discovery is retrievable by hypothesis
        repo = DiscoveryRepository(session)
        discoveries = repo.list_for_hypothesis(lineage.hypothesis_id)
        assert len(discoveries) == 1
        assert discoveries[0].discovery_id == res.discovery_id
        assert discoveries[0].lifecycle_state == DiscoveryLifecycleState.ACTIVE

        # Package 4 invalidation of Evidence updates Discovery to INVALIDATED
        propagate_validity_for_test(
            session,
            source_type=ValiditySourceType.EVIDENCE,
            source_id=lineage.evidence_id,
            event_type=ValidityEventType.EVIDENCE_INVALIDATION,
            reason="Post-commit data invalidation",
            idempotency_key="key:post_commit_invalidation_1",
        )

        session.expire_all()
        disc_after = repo.get_by_id(res.discovery_id)
        assert disc_after is not None
        assert disc_after.lifecycle_state == DiscoveryLifecycleState.INVALIDATED


# ============================================================================
# Section 9: Sole Writer Bypass Enforcement
# ============================================================================


def test_planner_commit_discovery_creation_bypasses_blocked(test_db_engine):
    with Session(test_db_engine) as session:
        from application.orchestrator.planner_commit import commit_planner_operations
        from schemas.enums import (
            PlannerNodeName,
            PlannerOperationApprovalState,
            PlannerOperationType,
        )
        from schemas.planner_operations import PlannerOperation

        op = PlannerOperation(
            operation_type=PlannerOperationType.CREATE_DISCOVERY,
            payload={"statement": "Bypass claim"},
            produced_by_node=PlannerNodeName.MANAGE_TASKS,
            approval_state=PlannerOperationApprovalState.APPROVED,
        )

        result = commit_planner_operations(session, [op])
        assert op.operation_id in result.failed_operation_ids
        assert "Discovery creation is owned by" in result.errors[op.operation_id]


def test_coordinator_cli_entry_point(test_db_engine):
    with Session(test_db_engine) as session:
        _, eval_control, _ = _setup_package2_ready_evaluation(session)
        grant = _issue_admission_authority(session)
        gov_service = DiscoveryAdmissionGovernanceService(
            session,
            workspace_id="workspace:test",
            session_id="session:test",
            principal_id="user:alice",
        )
        gov_service.record_governance_decision(
            evaluation_id=eval_control.evaluation_id,
            authority_id=grant.authority_id,
            decision=GovernanceDecisionOutcome.APPROVED,
        )

        coordinator = DiscoveryAdmissionCoordinator(
            session, workspace_id="workspace:test", session_id="session:test"
        )
        results = coordinator.process_eligible_admissions()

        assert len(results) == 1
        assert results[0].evaluation_id == eval_control.evaluation_id



# ============================================================================
# Section 10: Adversarial rollback, recovery, and exact-chain tests
# ============================================================================


@pytest.mark.parametrize(
    "failure_stage",
    [
        "lineage_guards",
        "discovery",
        "session_frame",
        "hypothesis",
        "task",
        "evaluation",
        "claim",
        "decision",
        "pre_commit",
    ],
)
def test_failure_after_each_atomic_stage_rolls_back_complete_chain(
    test_db_engine,
    failure_stage,
):
    with Session(test_db_engine) as session:
        lineage, evaluation, _, decision = _setup_authorized_admission(session)
        control = AtomicDiscoveryAdmissionService(
            session,
            workspace_id="workspace:test",
            session_id="session:test",
        )
        control.enqueue_admission(
            evaluation_id=evaluation.evaluation_id,
            decision_id=decision.decision_id,
        )
        lease = control.claim_admission(
            evaluation_id=evaluation.evaluation_id,
            decision_id=decision.decision_id,
            claim_owner="worker:failure-injection",
        )

        def inject(stage: str) -> None:
            if stage == failure_stage:
                raise RuntimeError(f"injected failure after {stage}")

        failing = AtomicDiscoveryAdmissionService(
            session,
            workspace_id="workspace:test",
            session_id="session:test",
            failure_injector=inject,
        )
        with pytest.raises(AtomicDiscoveryAdmissionError, match="injected failure"):
            failing.execute_claimed_admission(lease)

        session.expire_all()
        claim = session.get(DiscoveryAdmissionClaimRecord, lease.claim_id)
        hypothesis = session.get(HypothesisRecord, lineage.hypothesis_id)
        task = session.get(TaskRecord, lineage.task_id)
        evaluation_after = session.get(EvaluationControlRecord, evaluation.evaluation_id)
        decision_after = session.get(ProposalDecisionRecord, decision.decision_id)
        assert claim is not None and claim.state == DiscoveryAdmissionClaimState.CLAIMED
        assert hypothesis is not None
        assert hypothesis.status == HypothesisStatus.READY_FOR_EVALUATION
        assert task is not None and task.lifecycle_state == TaskLifecycleState.ACTIVE
        assert evaluation_after is not None
        assert evaluation_after.state == EvaluationControlState.PROPOSAL_READY
        assert decision_after is not None and decision_after.consumed is False
        assert session.exec(select(DiscoveryRecord)).all() == []
        assert session.exec(select(SessionFrameRecord)).all() == []


def test_failed_attempt_is_restart_safe_and_stale_lease_is_fenced(test_db_engine):
    with Session(test_db_engine) as session:
        _, evaluation, _, decision = _setup_authorized_admission(session)
        service = AtomicDiscoveryAdmissionService(
            session,
            workspace_id="workspace:test",
            session_id="session:test",
            failure_injector=lambda stage: (
                (_ for _ in ()).throw(RuntimeError("stop before commit"))
                if stage == "pre_commit"
                else None
            ),
        )
        service.enqueue_admission(
            evaluation_id=evaluation.evaluation_id,
            decision_id=decision.decision_id,
        )
        stale_lease = service.claim_admission(
            evaluation_id=evaluation.evaluation_id,
            decision_id=decision.decision_id,
            claim_owner="worker:stale",
        )
        with pytest.raises(AtomicDiscoveryAdmissionError, match="stop before commit"):
            service.execute_claimed_admission(stale_lease)

        session.exec(
            update(DiscoveryAdmissionClaimRecord)
            .where(DiscoveryAdmissionClaimRecord.claim_id == stale_lease.claim_id)
            .values(claim_expiry=utc_now() - timedelta(seconds=1))
        )
        session.commit()

        recovery = AtomicDiscoveryAdmissionService(
            session,
            workspace_id="workspace:test",
            session_id="session:test",
        )
        recovered_lease = recovery.reclaim_expired_admission(
            evaluation_id=evaluation.evaluation_id,
            decision_id=decision.decision_id,
            claim_owner="worker:recovered",
        )
        assert recovered_lease.fencing_epoch > stale_lease.fencing_epoch
        with pytest.raises(AtomicDiscoveryAdmissionConflictError, match="stale"):
            recovery.execute_claimed_admission(stale_lease)

        result = recovery.execute_claimed_admission(recovered_lease)
        assert result.disposition == DiscoveryAdmissionReplayDisposition.NEW


def test_cancelled_claim_rejects_stale_execution(test_db_engine):
    with Session(test_db_engine) as session:
        _, evaluation, _, decision = _setup_authorized_admission(session)
        service = AtomicDiscoveryAdmissionService(
            session,
            workspace_id="workspace:test",
            session_id="session:test",
        )
        service.enqueue_admission(
            evaluation_id=evaluation.evaluation_id,
            decision_id=decision.decision_id,
        )
        lease = service.claim_admission(
            evaluation_id=evaluation.evaluation_id,
            decision_id=decision.decision_id,
            claim_owner="worker:cancel",
        )
        service.cancel_claimed_admission(lease, reason="Operator cancelled queued admission.")

        with pytest.raises(AtomicDiscoveryAdmissionConflictError, match="stale"):
            service.execute_claimed_admission(lease)
        claim = session.get(DiscoveryAdmissionClaimRecord, lease.claim_id)
        assert claim is not None and claim.state == DiscoveryAdmissionClaimState.CANCELLED
        assert session.exec(select(DiscoveryRecord)).all() == []


def test_persisted_discovery_exactly_preserves_proposal_and_frame_excludes_assumptions(
    test_db_engine,
):
    with Session(test_db_engine) as session:
        _, evaluation, proposal, decision = _setup_authorized_admission(session)
        result = AtomicDiscoveryAdmissionService(
            session,
            workspace_id="workspace:test",
            session_id="session:test",
        ).execute_admission(
            evaluation_id=evaluation.evaluation_id,
            decision_id=decision.decision_id,
        )

        discovery = DiscoveryRepository(session).get_by_id(result.discovery_id)
        frame = session.get(SessionFrameRecord, result.session_frame_id)
        assert discovery is not None and frame is not None
        assert discovery.claim == proposal.claim
        assert discovery.epistemic_status == proposal.epistemic_status
        assert discovery.scope == proposal.scope
        assert discovery.evidence_ids == list(proposal.evidence_ids)
        assert discovery.validity_basis == proposal.validity_basis
        assert discovery.uncertainty == proposal.validity_basis.uncertainty
        assert discovery.limitations == list(proposal.limitations)
        assert discovery.invalidators == list(proposal.validity_basis.invalidators)
        assert frame.active_assumption_refs == []
        assert frame.active_assumptions == []
        assert frame.relevant_discovery_refs == [str(result.discovery_id)]


def test_direct_terminal_child_completes_without_completing_parent(test_db_engine):
    with Session(test_db_engine) as session:
        lineage, evaluation, _, decision = _setup_authorized_admission(session)
        terminal = session.get(TaskRecord, lineage.task_id)
        assert terminal is not None
        parent = TaskRepository(session).create(
            Task(
                title="Organizing parent",
                description="Must remain active when its direct analytical child completes.",
                task_kind=TaskKind.ORGANIZING,
                lifecycle_state=TaskLifecycleState.ACTIVE,
            )
        )
        session.exec(
            update(TaskRecord)
            .where(TaskRecord.task_id == terminal.task_id)
            .values(parent_task_id=parent.task_id)
        )
        session.commit()

        AtomicDiscoveryAdmissionService(
            session,
            workspace_id="workspace:test",
            session_id="session:test",
        ).execute_admission(
            evaluation_id=evaluation.evaluation_id,
            decision_id=decision.decision_id,
        )
        session.expire_all()
        assert session.get(TaskRecord, terminal.task_id).lifecycle_state == (
            TaskLifecycleState.COMPLETED
        )
        assert session.get(TaskRecord, parent.task_id).lifecycle_state == (
            TaskLifecycleState.ACTIVE
        )


def test_replay_rejects_tampered_session_frame(test_db_engine):
    with Session(test_db_engine) as session:
        _, evaluation, _, decision = _setup_authorized_admission(session)
        service = AtomicDiscoveryAdmissionService(
            session,
            workspace_id="workspace:test",
            session_id="session:test",
        )
        result = service.execute_admission(
            evaluation_id=evaluation.evaluation_id,
            decision_id=decision.decision_id,
        )
        session.exec(
            update(SessionFrameRecord)
            .where(SessionFrameRecord.session_frame_id == result.session_frame_id)
            .values(key_warnings=["tampered frame"])
        )
        session.commit()

        with pytest.raises(AtomicDiscoveryAdmissionConflictError, match="SessionFrame"):
            service.execute_admission(
                evaluation_id=evaluation.evaluation_id,
                decision_id=decision.decision_id,
            )


def test_exact_decision_consumption_cannot_be_reversed(test_db_engine):
    with Session(test_db_engine) as session:
        _, evaluation, _, decision = _setup_authorized_admission(session)
        AtomicDiscoveryAdmissionService(
            session,
            workspace_id="workspace:test",
            session_id="session:test",
        ).execute_admission(
            evaluation_id=evaluation.evaluation_id,
            decision_id=decision.decision_id,
        )
        with pytest.raises(IntegrityError, match="one-way"):
            session.exec(
                update(ProposalDecisionRecord)
                .where(ProposalDecisionRecord.decision_id == decision.decision_id)
                .values(consumed=False, consumed_at=None, consumed_by=None)
            )
            session.commit()
        session.rollback()


# ============================================================================
# Section 11: Overlapping independent-session races
# ============================================================================


def test_duplicate_admission_claim_race_has_one_fenced_winner(test_db_engine):
    with Session(test_db_engine) as setup_session:
        _, evaluation, _, decision = _setup_authorized_admission(setup_session)
        AtomicDiscoveryAdmissionService(
            setup_session,
            workspace_id="workspace:test",
            session_id="session:test",
        ).enqueue_admission(
            evaluation_id=evaluation.evaluation_id,
            decision_id=decision.decision_id,
        )
        evaluation_id = evaluation.evaluation_id
        decision_id = decision.decision_id

    database_url = str(test_db_engine.url)
    barrier = Barrier(2)

    def compete(owner: str):
        worker_session = get_session(database_url)
        try:
            barrier.wait(timeout=5)
            try:
                return AtomicDiscoveryAdmissionService(
                    worker_session,
                    workspace_id="workspace:test",
                    session_id="session:test",
                ).claim_admission(
                    evaluation_id=evaluation_id,
                    decision_id=decision_id,
                    claim_owner=owner,
                )
            except AtomicDiscoveryAdmissionConflictError:
                return None
        finally:
            worker_session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        leases = list(pool.map(compete, ("worker:one", "worker:two")))
    winners = [lease for lease in leases if lease is not None]
    assert len(winners) == 1

    with Session(test_db_engine) as admission_session:
        result = AtomicDiscoveryAdmissionService(
            admission_session,
            workspace_id="workspace:test",
            session_id="session:test",
        ).execute_claimed_admission(winners[0])
        assert result.disposition == DiscoveryAdmissionReplayDisposition.NEW
        assert len(admission_session.exec(select(DiscoveryRecord)).all()) == 1


def test_package4_wins_before_claim_execution_and_invalidates_claim(test_db_engine):
    with Session(test_db_engine) as session:
        lineage, evaluation, _, decision = _setup_authorized_admission(session)
        service = AtomicDiscoveryAdmissionService(
            session,
            workspace_id="workspace:test",
            session_id="session:test",
        )
        service.enqueue_admission(
            evaluation_id=evaluation.evaluation_id,
            decision_id=decision.decision_id,
        )
        lease = service.claim_admission(
            evaluation_id=evaluation.evaluation_id,
            decision_id=decision.decision_id,
            claim_owner="worker:validity-loser",
        )

        result = propagate_validity_for_test(
            session,
            source_type=ValiditySourceType.EVIDENCE,
            source_id=lineage.evidence_id,
            event_type=ValidityEventType.EVIDENCE_INVALIDATION,
            reason="Validity won before Discovery staging.",
            idempotency_key="key:package4-wins-before-admission",
        )
        assert result.affected_admission_claim_count == 1
        with pytest.raises(AtomicDiscoveryAdmissionConflictError, match="stale"):
            service.execute_claimed_admission(lease)
        claim = session.get(DiscoveryAdmissionClaimRecord, lease.claim_id)
        assert claim is not None and claim.state == DiscoveryAdmissionClaimState.INVALIDATED
        assert session.exec(select(DiscoveryRecord)).all() == []


@pytest.mark.parametrize(
    "validity_event",
    [
        ValidityEventType.EVIDENCE_INVALIDATION,
        ValidityEventType.EVIDENCE_SUPERSESSION,
    ],
)
def test_admission_and_package4_overlap_to_one_coherent_invalidated_state(
    test_db_engine,
    validity_event,
):
    with Session(test_db_engine) as setup_session:
        lineage, evaluation, _, decision = _setup_authorized_admission(setup_session)
        evidence_id = lineage.evidence_id
        evaluation_id = evaluation.evaluation_id
        decision_id = decision.decision_id

    database_url = str(test_db_engine.url)
    guards_acquired = Event()
    release_admission = Event()
    validity_started = Event()
    race_state: dict[str, object] = {}

    def inject(stage: str) -> None:
        if stage == "lineage_guards":
            guards_acquired.set()
            assert release_admission.wait(timeout=10)

    def admit():
        worker_session = get_session(database_url)
        try:
            return AtomicDiscoveryAdmissionService(
                worker_session,
                workspace_id="workspace:test",
                session_id="session:test",
                failure_injector=inject,
            ).execute_admission(
                evaluation_id=evaluation_id,
                decision_id=decision_id,
                claim_owner="worker:overlap",
            )
        finally:
            worker_session.close()

    def invalidate():
        worker_session = get_session(database_url)
        try:
            assert guards_acquired.wait(timeout=10)
            validity_started.set()
            replacement_id = None
            if validity_event == ValidityEventType.EVIDENCE_SUPERSESSION:
                source = EvidenceRepository(worker_session).get_by_id(evidence_id)
                assert source is not None
                replacement = source.model_copy(
                    update={
                        "evidence_id": uuid4(),
                        "limitations": [
                            *source.limitations,
                            "Replacement Evidence created during the overlap.",
                        ],
                    }
                )
                EvidenceRepository(
                    worker_session
                )._stage_create_from_evidence_admission(replacement)
                worker_session.commit()
                replacement_id = replacement.evidence_id
                race_state["replacement_id"] = replacement_id
            try:
                return propagate_validity_for_test(
                    worker_session,
                    source_type=ValiditySourceType.EVIDENCE,
                    source_id=evidence_id,
                    event_type=validity_event,
                    reason="Overlapping validity event.",
                    idempotency_key=f"key:overlap-{validity_event.value}",
                    replacement_id=replacement_id,
                )
            except Exception:
                return None
        finally:
            worker_session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        admission_future = pool.submit(admit)
        assert guards_acquired.wait(timeout=10)
        validity_future = pool.submit(invalidate)
        assert validity_started.wait(timeout=10)
        release_admission.set()
        admission_result = admission_future.result(timeout=15)
        validity_result = validity_future.result(timeout=15)

    with Session(test_db_engine) as verification:
        if validity_result is None:
            validity_result = propagate_validity_for_test(
                verification,
                source_type=ValiditySourceType.EVIDENCE,
                source_id=evidence_id,
                event_type=validity_event,
                reason="Retry after admission won the overlap.",
                idempotency_key=f"key:overlap-{validity_event.value}-retry",
                replacement_id=race_state.get("replacement_id"),
            )
        discovery = verification.get(DiscoveryRecord, admission_result.discovery_id)
        frame = verification.get(SessionFrameRecord, admission_result.session_frame_id)
        assert validity_result.affected_discovery_count == 1
        assert discovery is not None
        assert discovery.lifecycle_state == DiscoveryLifecycleState.INVALIDATED
        assert frame is not None and frame.stale_context
        assert (
            DiscoveryRepository(verification).list(
                hypothesis_id=admission_result.hypothesis_id,
                lifecycle_state=DiscoveryLifecycleState.ACTIVE,
            )
            == []
        )


def test_package5_upgrade_adds_replay_authority_and_quarantines_legacy_claim(
    tmp_path: Path,
):
    from db.session import create_db_engine

    database_url = f"sqlite:///{(tmp_path / 'package5-upgrade.sqlite3').as_posix()}"
    create_db_engine.cache_clear()
    engine = create_db_engine(database_url)
    legacy_claim_id = uuid4().hex
    now = utc_now().isoformat()
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE discovery_admission_claims ("
                "claim_id CHAR(32) PRIMARY KEY, "
                "evaluation_id CHAR(32) NOT NULL, "
                "decision_id CHAR(32) NOT NULL, "
                "proposal_digest VARCHAR NOT NULL, "
                "bundle_digest VARCHAR NOT NULL, "
                "admission_fingerprint VARCHAR NOT NULL, "
                "owner VARCHAR, claim_time DATETIME, claim_expiry DATETIME, "
                "fencing_epoch INTEGER NOT NULL DEFAULT 0, "
                "attempt_number INTEGER NOT NULL DEFAULT 1, "
                "state VARCHAR NOT NULL, invalidation_reason TEXT, "
                "created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO discovery_admission_claims "
                "(claim_id, evaluation_id, decision_id, proposal_digest, bundle_digest, "
                "admission_fingerprint, owner, fencing_epoch, attempt_number, state, "
                "created_at, updated_at) "
                "VALUES (:claim_id, :evaluation_id, :decision_id, 'proposal', 'bundle', "
                "'admission', 'legacy-worker', 1, 1, 'COMMITTED', :now, :now)"
            ),
            {
                "claim_id": legacy_claim_id,
                "evaluation_id": uuid4().hex,
                "decision_id": uuid4().hex,
                "now": now,
            },
        )

    init_db(database_url)
    upgraded = create_db_engine(database_url)
    columns = {
        column["name"]
        for column in inspect_database(upgraded).get_columns("discovery_admission_claims")
    }
    assert {
        "claim_token_digest",
        "discovery_id",
        "discovery_fingerprint",
        "session_frame_id",
        "session_frame_fingerprint",
        "committed_at",
    }.issubset(columns)
    with upgraded.connect() as connection:
        state, reason = connection.execute(
            text(
                "SELECT state, invalidation_reason "
                "FROM discovery_admission_claims WHERE claim_id = :claim_id"
            ),
            {"claim_id": legacy_claim_id},
        ).one()
        trigger_names = {
            row[0]
            for row in connection.execute(
                text("SELECT name FROM sqlite_master WHERE type = 'trigger'")
            )
        }
    assert state == DiscoveryAdmissionClaimState.CONFLICT.name
    assert "legacy Package 5 claim" in reason
    assert "discovery_admission_claims_terminal" in trigger_names
    assert "proposal_decisions_exact_consumption" in trigger_names
    create_db_engine.cache_clear()
