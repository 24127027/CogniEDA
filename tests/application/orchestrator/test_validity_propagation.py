"""Production-backed adversarial tests for Package 4 validity propagation."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import delete, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, create_engine

from application.evaluation import (
    EvaluationTransitionService,
    StaleEvaluationOwnerError,
)
from application.governance import (
    DiscoveryAdmissionGovernanceService,
)
from application.orchestrator.validity_propagation_service import (
    AtomicValidityPropagationService,
    PartialValidityPropagationError,
    StaleValidityPropagationError,
    validity_authority_scope,
)
from db.init_db import init_db
from db.models import (
    AnalysisFrameRecord,
    DataProfileRecord,
    DiscoveryRecord,
    EvaluationControlRecord,
    EvidenceRecord,
    ExecutionRunRecord,
    HypothesisRecord,
    ProposalDecisionRecord,
    SessionFrameRecord,
    TaskRecord,
    ValidityEventRecord,
)
from db.session import create_db_engine, get_session
from memory.retrieval_engine import DiscoveryRetrievalEngine
from memory.session_frame import SessionContextBuilder
from package2_helpers import (
    persist_governance_authority,
    persist_package2_lineage,
    proposal_for_bundle,
)
from repositories.data_profile_repository import DataProfileRepository
from repositories.discovery_repository import DiscoveryRepository
from repositories.evidence_repository import EvidenceRepository
from repositories.session_frame_repository import SessionFrameRepository
from schemas.artifacts import DataProfile, Evidence
from schemas.common import (
    BaselineSummary,
    SchemaSummary,
)
from schemas.enums import (
    AuthorizationClass,
    ContextMode,
    DataProfileLifecycleState,
    DataProfileMethod,
    DatasetSourceType,
    DiscoveryEpistemicStatus,
    DiscoveryLifecycleState,
    EvaluationControlState,
    EvidenceLifecycleState,
    EvidenceType,
    GovernanceDecisionOutcome,
    HypothesisStatus,
    SessionFrameStatus,
    TaskLifecycleState,
    ValidityEventType,
    ValiditySourceState,
    ValiditySourceType,
)
from schemas.retrieval import RetrievalRequest
from schemas.validity_propagation_contracts import ValidityPropagationCommand

_WORKSPACE = "ws-validity-1"
_SESSION = "sess-validity-1"


def _validity_grant(
    session: Session,
    event_type: ValidityEventType,
    *,
    source_type: ValiditySourceType,
    source_id: UUID,
    replacement_id: UUID | None = None,
    authority_class: AuthorizationClass = AuthorizationClass.TRUSTED_INTERNAL,
    actor_identity: str = "system_integrity",
):
    purpose, operation = validity_authority_scope(
        event_type=event_type,
        source_type=source_type,
        source_id=source_id,
        replacement_id=replacement_id,
    )
    return persist_governance_authority(
        session,
        authority_class=authority_class,
        actor_identity=actor_identity,
        workspace_id=_WORKSPACE,
        session_id=None if authority_class == AuthorizationClass.TRUSTED_INTERNAL else _SESSION,
        purpose=purpose,
        operation_type=operation,
    )


def _command(
    session: Session,
    *,
    source_type: ValiditySourceType,
    source_id: UUID,
    event_type: ValidityEventType,
    authority_id: UUID,
    key: str,
    reason: str = "Persisted source validity was lost.",
    session_id: str | None = None,
    replacement_id: UUID | None = None,
) -> ValidityPropagationCommand:
    service = AtomicValidityPropagationService(session)
    source_state, source_fingerprint = service.load_source_guard(source_type, source_id)
    replacement_fingerprint = None
    if replacement_id is not None:
        _, replacement_fingerprint = service.load_source_guard(source_type, replacement_id)
    return ValidityPropagationCommand(
        source_type=source_type,
        source_id=source_id,
        event_type=event_type,
        reason=reason,
        authority_id=authority_id,
        workspace_id=_WORKSPACE,
        session_id=session_id,
        expected_source_state=source_state,
        expected_source_fingerprint=source_fingerprint,
        idempotency_key=key,
        replacement_id=replacement_id,
        expected_replacement_fingerprint=replacement_fingerprint,
    )


def _seed_validity_lineage(session: Session, *, with_discovery: bool = True):
    lineage = persist_package2_lineage(session)
    evaluations = EvaluationTransitionService(session)
    control, _ = evaluations.enqueue_evaluation(hypothesis_id=lineage.hypothesis_id)
    claimed = evaluations.claim_evaluation(
        evaluation_id=control.evaluation_id,
        owner="test_worker",
        claim_duration_seconds=300,
    )
    bundle = evaluations.load_claimed_bundle(
        evaluation_id=control.evaluation_id,
        owner="test_worker",
        fencing_epoch=claimed.fencing_epoch,
        source_bundle_digest=claimed.bundle_digest,
    )
    proposal = proposal_for_bundle(bundle)
    ready = evaluations.publish_proposal(
        evaluation_id=control.evaluation_id,
        owner="test_worker",
        fencing_epoch=claimed.fencing_epoch,
        source_bundle_digest=claimed.bundle_digest,
        proposal=proposal,
    )
    admission_grant = persist_governance_authority(
        session,
        workspace_id=_WORKSPACE,
        session_id=_SESSION,
        actor_identity="test_governor",
    )
    decision = DiscoveryAdmissionGovernanceService(
        session=session,
        workspace_id=_WORKSPACE,
        session_id=_SESSION,
    ).record_governance_decision(
        evaluation_id=ready.evaluation_id,
        authority_id=admission_grant.authority_id,
        decision=GovernanceDecisionOutcome.APPROVED,
    )

    discovery_id = None
    discovery_refs: list[str] = []
    if with_discovery:
        discovery = DiscoveryRecord(
            discovery_id=uuid4(),
            hypothesis_id=lineage.hypothesis_id,
            evidence_ids=[str(lineage.evidence_id)],
            claim=proposal.claim.model_dump(mode="json"),
            epistemic_status=proposal.epistemic_status,
            scope=proposal.scope,
            validity_basis=proposal.validity_basis.model_dump(mode="json"),
            lifecycle_state=DiscoveryLifecycleState.ACTIVE,
        )
        session.add(discovery)
        session.commit()
        discovery_id = discovery.discovery_id
        discovery_refs = [str(discovery.discovery_id)]

    frame = SessionFrameRecord(
        session_frame_id=uuid4(),
        frame_topic="Active Research Topic",
        frame_status=SessionFrameStatus.ACTIVE,
        objective_snapshot="Objective snapshot",
        active_data_profile_refs=[str(lineage.profile_id)],
        supporting_evidence_refs=[str(lineage.evidence_id)],
        relevant_discovery_refs=discovery_refs,
        active_hypothesis_refs=[str(lineage.hypothesis_id)],
        active_task_refs=[str(lineage.task_id)],
    )
    session.add(frame)
    session.commit()
    return {
        "profile_id": lineage.profile_id,
        "task_id": lineage.task_id,
        "hypothesis_id": lineage.hypothesis_id,
        "analysis_frame_id": lineage.analysis_frame_id,
        "execution_run_id": lineage.execution_run_id,
        "evidence_id": lineage.evidence_id,
        "evaluation_id": ready.evaluation_id,
        "decision_id": decision.decision_id,
        "discovery_id": discovery_id,
        "session_frame_id": frame.session_frame_id,
    }


def _replacement_evidence(session: Session, source_id: UUID) -> UUID:
    source = EvidenceRepository(session).get_by_id(source_id)
    assert source is not None
    replacement = Evidence(
        hypothesis_id=source.hypothesis_id,
        profile_id=source.profile_id,
        analysis_frame_ref=source.analysis_frame_ref,
        execution_run_ref=source.execution_run_ref,
        evidence_type=EvidenceType.EXPERIMENT_RESULT,
        method=source.method,
        parameters=source.parameters,
        provenance=source.provenance,
        result_summary=source.result_summary,
        limitations=["Replacement validation pending review."],
    )
    EvidenceRepository(session)._stage_create_from_evidence_admission(replacement)
    session.commit()
    return replacement.evidence_id


def _replacement_profile(session: Session, source_id: UUID) -> UUID:
    source = DataProfileRepository(session).get_by_id(source_id)
    assert source is not None
    replacement = DataProfile(
        dataset_path=source.dataset_path,
        source_type=DatasetSourceType.FILE,
        dvc_hash="dvc:protected-v2",
        method=DataProfileMethod.INFERRED_SCHEMA,
        schema_summary=SchemaSummary(column_order=["x", "y"]),
        baseline_summary=BaselineSummary(column_names=["x", "y"]),
        row_count=source.row_count,
        column_count=source.column_count,
        lifecycle_state=DataProfileLifecycleState.ACTIVE,
        accepted_as_ground_truth=True,
    )
    return DataProfileRepository(session).create(replacement).profile_id


def test_evidence_invalidation_is_complete_atomic_and_scientifically_immutable(
    db_session,
) -> None:
    seed = _seed_validity_lineage(db_session)
    grant = _validity_grant(
        db_session,
        ValidityEventType.EVIDENCE_INVALIDATION,
        source_type=ValiditySourceType.EVIDENCE,
        source_id=seed["evidence_id"],
        authority_class=AuthorizationClass.USER_GOVERNED,
        actor_identity="test_governor",
    )
    command = _command(
        db_session,
        source_type=ValiditySourceType.EVIDENCE,
        source_id=seed["evidence_id"],
        event_type=ValidityEventType.EVIDENCE_INVALIDATION,
        authority_id=grant.authority_id,
        session_id=_SESSION,
        key="evidence-invalidation-1",
        reason="Instrument calibration failure.",
    )
    evidence_before = db_session.get(EvidenceRecord, seed["evidence_id"])
    discovery_before = db_session.get(DiscoveryRecord, seed["discovery_id"])
    immutable_evidence = evidence_before.model_dump(
        exclude={"lifecycle_state", "superseded_by_evidence_id", "lifecycle_reason"}
    )
    immutable_discovery = discovery_before.model_dump(
        exclude={"lifecycle_state", "review_reasons", "flagged_by_evidence_ids"}
    )

    result = AtomicValidityPropagationService(db_session).execute_propagation(command)

    evidence = db_session.get(EvidenceRecord, seed["evidence_id"])
    control = db_session.get(EvaluationControlRecord, seed["evaluation_id"])
    decision = db_session.get(ProposalDecisionRecord, seed["decision_id"])
    discovery = db_session.get(DiscoveryRecord, seed["discovery_id"])
    hypothesis = db_session.get(HypothesisRecord, seed["hypothesis_id"])
    task = db_session.get(TaskRecord, seed["task_id"])
    frame = db_session.get(SessionFrameRecord, seed["session_frame_id"])
    assert result.affected_evidence_count == 1
    assert evidence.lifecycle_state == EvidenceLifecycleState.INVALIDATED
    assert control.state == EvaluationControlState.INVALIDATED
    assert decision.decision == GovernanceDecisionOutcome.APPROVED
    assert decision.consumed is False
    assert discovery.lifecycle_state == DiscoveryLifecycleState.INVALIDATED
    assert discovery.epistemic_status == DiscoveryEpistemicStatus.SUPPORTED
    assert hypothesis.status == HypothesisStatus.READY_FOR_EVALUATION
    assert any(str(result.event_id) in item for item in hypothesis.review_reasons)
    assert task.lifecycle_state == TaskLifecycleState.ACTIVE
    assert any(str(result.event_id) in item for item in task.review_reasons)
    assert frame.frame_status == SessionFrameStatus.SUPERSEDED
    assert (
        evidence.model_dump(
            exclude={"lifecycle_state", "superseded_by_evidence_id", "lifecycle_reason"}
        )
        == immutable_evidence
    )
    assert (
        discovery.model_dump(
            exclude={"lifecycle_state", "review_reasons", "flagged_by_evidence_ids"}
        )
        == immutable_discovery
    )


@pytest.mark.parametrize(
    ("source_type", "event_type", "seed_key", "expected_state"),
    [
        (
            ValiditySourceType.EVIDENCE,
            ValidityEventType.EVIDENCE_CONFLICT,
            "evidence_id",
            EvidenceLifecycleState.INVALIDATED,
        ),
        (
            ValiditySourceType.DATA_PROFILE,
            ValidityEventType.DATA_PROFILE_INVALIDATION,
            "profile_id",
            DataProfileLifecycleState.INVALIDATED,
        ),
        (
            ValiditySourceType.ANALYSIS_FRAME,
            ValidityEventType.ANALYSIS_FRAME_INVALIDITY,
            "analysis_frame_id",
            ValiditySourceState.INVALIDATED,
        ),
        (
            ValiditySourceType.EXECUTION_RUN,
            ValidityEventType.EXECUTION_RUN_CONFLICT,
            "execution_run_id",
            ValiditySourceState.CONFLICT,
        ),
        (
            ValiditySourceType.ANALYSIS_FRAME,
            ValidityEventType.PROVENANCE_CORRUPTION,
            "analysis_frame_id",
            ValiditySourceState.INVALIDATED,
        ),
    ],
)
def test_supported_non_supersession_events_traverse_repository_lineage(
    db_session,
    source_type,
    event_type,
    seed_key,
    expected_state,
) -> None:
    seed = _seed_validity_lineage(db_session, with_discovery=False)
    grant = _validity_grant(
        db_session,
        event_type,
        source_type=source_type,
        source_id=seed[seed_key],
    )
    command = _command(
        db_session,
        source_type=source_type,
        source_id=seed[seed_key],
        event_type=event_type,
        authority_id=grant.authority_id,
        key=f"{event_type.value}-1",
    )
    result = AtomicValidityPropagationService(db_session).execute_propagation(command)
    if source_type == ValiditySourceType.EVIDENCE:
        source = db_session.get(EvidenceRecord, seed[seed_key])
        assert source.lifecycle_state == expected_state
    elif source_type == ValiditySourceType.DATA_PROFILE:
        source = db_session.get(DataProfileRecord, seed[seed_key])
        assert source.lifecycle_state == expected_state
    elif source_type == ValiditySourceType.ANALYSIS_FRAME:
        source = db_session.get(AnalysisFrameRecord, seed[seed_key])
        assert source.validity_state == expected_state
    else:
        source = db_session.get(ExecutionRunRecord, seed[seed_key])
        assert source.validity_state == expected_state
    evidence = db_session.get(EvidenceRecord, seed["evidence_id"])
    assert evidence.lifecycle_state == EvidenceLifecycleState.INVALIDATED
    assert result.affected_evaluation_count == 1


@pytest.mark.parametrize(
    ("source_type", "event_type", "seed_key", "replacement_factory"),
    [
        (
            ValiditySourceType.EVIDENCE,
            ValidityEventType.EVIDENCE_SUPERSESSION,
            "evidence_id",
            _replacement_evidence,
        ),
        (
            ValiditySourceType.DATA_PROFILE,
            ValidityEventType.DATA_PROFILE_SUPERSESSION,
            "profile_id",
            _replacement_profile,
        ),
    ],
)
def test_supersession_requires_verified_persisted_replacement(
    db_session,
    source_type,
    event_type,
    seed_key,
    replacement_factory,
) -> None:
    seed = _seed_validity_lineage(db_session, with_discovery=False)
    replacement_id = replacement_factory(db_session, seed[seed_key])
    grant = _validity_grant(
        db_session,
        event_type,
        source_type=source_type,
        source_id=seed[seed_key],
        replacement_id=replacement_id,
    )
    command = _command(
        db_session,
        source_type=source_type,
        source_id=seed[seed_key],
        event_type=event_type,
        authority_id=grant.authority_id,
        key=f"{event_type.value}-1",
        replacement_id=replacement_id,
    )
    alternate_replacement_id = replacement_factory(db_session, seed[seed_key])
    _, alternate_fingerprint = AtomicValidityPropagationService(db_session).load_source_guard(
        source_type,
        alternate_replacement_id,
    )
    forged_replacement = command.model_copy(
        update={
            "idempotency_key": f"{event_type.value}-forged-replacement",
            "replacement_id": alternate_replacement_id,
            "expected_replacement_fingerprint": alternate_fingerprint,
        }
    )
    with pytest.raises(PermissionError, match="purpose/operation"):
        AtomicValidityPropagationService(db_session).execute_propagation(forged_replacement)

    AtomicValidityPropagationService(db_session).execute_propagation(command)
    if source_type == ValiditySourceType.EVIDENCE:
        source = db_session.get(EvidenceRecord, seed[seed_key])
        assert source.lifecycle_state == EvidenceLifecycleState.SUPERSEDED
        assert source.superseded_by_evidence_id == replacement_id
    else:
        source = db_session.get(DataProfileRecord, seed[seed_key])
        assert source.lifecycle_state == DataProfileLifecycleState.SUPERSEDED
        assert source.superseded_by_data_profile_id == replacement_id


def test_authority_is_durable_exact_and_not_caller_declared(db_session) -> None:
    seed = _seed_validity_lineage(db_session, with_discovery=False)
    valid = _validity_grant(
        db_session,
        ValidityEventType.EVIDENCE_INVALIDATION,
        source_type=ValiditySourceType.EVIDENCE,
        source_id=seed["evidence_id"],
    )
    command = _command(
        db_session,
        source_type=ValiditySourceType.EVIDENCE,
        source_id=seed["evidence_id"],
        event_type=ValidityEventType.EVIDENCE_INVALIDATION,
        authority_id=valid.authority_id,
        key="authority-exact",
    )
    with pytest.raises(ValidationError, match="authority_identity"):
        ValidityPropagationCommand(**command.model_dump(), authority_identity="system_integrity")

    wrong_purpose = persist_governance_authority(
        db_session,
        authority_class=AuthorizationClass.TRUSTED_INTERNAL,
        actor_identity="system_integrity",
        workspace_id=_WORKSPACE,
        session_id=None,
        purpose="governed_discovery_admission",
        operation_type="authorize_proposal",
    )
    wrong_command = command.model_copy(
        update={
            "authority_id": wrong_purpose.authority_id,
            "idempotency_key": "wrong-purpose",
        }
    )
    with pytest.raises(PermissionError, match="purpose/operation"):
        AtomicValidityPropagationService(db_session).execute_propagation(wrong_command)

    other_source_purpose, other_source_operation = validity_authority_scope(
        event_type=ValidityEventType.EVIDENCE_INVALIDATION,
        source_type=ValiditySourceType.EVIDENCE,
        source_id=uuid4(),
    )
    other_source = persist_governance_authority(
        db_session,
        authority_class=AuthorizationClass.TRUSTED_INTERNAL,
        actor_identity="system_integrity",
        workspace_id=_WORKSPACE,
        session_id=None,
        purpose=other_source_purpose,
        operation_type=other_source_operation,
    )
    with pytest.raises(PermissionError, match="purpose/operation"):
        AtomicValidityPropagationService(db_session).execute_propagation(
            command.model_copy(
                update={
                    "authority_id": other_source.authority_id,
                    "idempotency_key": "wrong-source-capability",
                }
            )
        )

    exact_purpose, exact_operation = validity_authority_scope(
        event_type=command.event_type,
        source_type=command.source_type,
        source_id=command.source_id,
    )
    untrusted = persist_governance_authority(
        db_session,
        authority_class=AuthorizationClass.TRUSTED_INTERNAL,
        actor_identity="caller_declared_trusted",
        workspace_id=_WORKSPACE,
        session_id=None,
        purpose=exact_purpose,
        operation_type=exact_operation,
    )
    with pytest.raises(PermissionError, match="allow-listed"):
        AtomicValidityPropagationService(db_session).execute_propagation(
            command.model_copy(
                update={
                    "authority_id": untrusted.authority_id,
                    "idempotency_key": "untrusted-actor",
                }
            )
        )

    valid.authority_fingerprint = "caller-forged"
    db_session.add(valid)
    db_session.commit()
    with pytest.raises(PermissionError, match="fingerprint"):
        AtomicValidityPropagationService(db_session).execute_propagation(command)


def test_exact_replay_requires_complete_committed_effects(db_session) -> None:
    seed = _seed_validity_lineage(db_session)
    grant = _validity_grant(
        db_session,
        ValidityEventType.EVIDENCE_INVALIDATION,
        source_type=ValiditySourceType.EVIDENCE,
        source_id=seed["evidence_id"],
    )
    command = _command(
        db_session,
        source_type=ValiditySourceType.EVIDENCE,
        source_id=seed["evidence_id"],
        event_type=ValidityEventType.EVIDENCE_INVALIDATION,
        authority_id=grant.authority_id,
        key="exact-replay",
    )
    service = AtomicValidityPropagationService(db_session)
    first = service.execute_propagation(command)
    second = service.execute_propagation(command)
    assert second.replayed is True
    assert second.event_id == first.event_id
    changed = command.model_copy(update={"reason": "Changed reason."})
    with pytest.raises(ValueError, match="another event"):
        service.execute_propagation(changed)

    task = db_session.get(TaskRecord, seed["task_id"])
    task.review_reasons = []
    db_session.add(task)
    db_session.commit()
    with pytest.raises(PartialValidityPropagationError):
        service.execute_propagation(command)


@pytest.mark.parametrize("fail_after_write", range(1, 8))
def test_failure_after_each_staged_write_rolls_back(
    db_session,
    fail_after_write,
) -> None:
    seed = _seed_validity_lineage(db_session)
    grant = _validity_grant(
        db_session,
        ValidityEventType.EVIDENCE_INVALIDATION,
        source_type=ValiditySourceType.EVIDENCE,
        source_id=seed["evidence_id"],
    )
    command = _command(
        db_session,
        source_type=ValiditySourceType.EVIDENCE,
        source_id=seed["evidence_id"],
        event_type=ValidityEventType.EVIDENCE_INVALIDATION,
        authority_id=grant.authority_id,
        key=f"rollback-{fail_after_write}",
    )
    writes = 0

    def fail(stage: str) -> None:
        nonlocal writes
        writes += 1
        if writes == fail_after_write:
            raise RuntimeError(f"injected after {stage}")

    with pytest.raises(RuntimeError, match="injected"):
        AtomicValidityPropagationService(
            db_session,
            failure_injector=fail,
        ).execute_propagation(command)
    assert writes >= fail_after_write
    assert (
        db_session.get(EvidenceRecord, seed["evidence_id"]).lifecycle_state
        == EvidenceLifecycleState.ACTIVE
    )
    assert (
        db_session.get(EvaluationControlRecord, seed["evaluation_id"]).state
        == EvaluationControlState.PROPOSAL_READY
    )
    assert (
        db_session.get(DiscoveryRecord, seed["discovery_id"]).lifecycle_state
        == DiscoveryLifecycleState.ACTIVE
    )
    assert db_session.exec(text("SELECT COUNT(*) FROM validity_events")).one()[0] == 0


def test_stale_owner_and_existing_decision_lose_eligibility(db_session) -> None:
    seed = _seed_validity_lineage(db_session, with_discovery=False)
    governance = DiscoveryAdmissionGovernanceService(
        session=db_session,
        workspace_id=_WORKSPACE,
        session_id=_SESSION,
    )
    detached_plan = governance.create_admission_plan(
        evaluation_id=seed["evaluation_id"],
        decision_id=seed["decision_id"],
    )
    grant = _validity_grant(
        db_session,
        ValidityEventType.EVIDENCE_INVALIDATION,
        source_type=ValiditySourceType.EVIDENCE,
        source_id=seed["evidence_id"],
    )
    command = _command(
        db_session,
        source_type=ValiditySourceType.EVIDENCE,
        source_id=seed["evidence_id"],
        event_type=ValidityEventType.EVIDENCE_INVALIDATION,
        authority_id=grant.authority_id,
        key="decision-ineligible",
    )
    AtomicValidityPropagationService(db_session).execute_propagation(command)
    decision = db_session.get(ProposalDecisionRecord, seed["decision_id"])
    assert decision.decision == GovernanceDecisionOutcome.APPROVED
    assert decision.consumed is False
    with pytest.raises(ValueError):
        governance.create_admission_plan(
            evaluation_id=seed["evaluation_id"],
            decision_id=seed["decision_id"],
        )
    assert detached_plan.expected_evaluation_state == EvaluationControlState.PROPOSAL_READY


def test_claimed_worker_cannot_publish_after_validity_commit(db_session) -> None:
    lineage = persist_package2_lineage(db_session)
    evaluations = EvaluationTransitionService(db_session)
    control, _ = evaluations.enqueue_evaluation(hypothesis_id=lineage.hypothesis_id)
    claimed = evaluations.claim_evaluation(
        evaluation_id=control.evaluation_id,
        owner="worker-1",
        claim_duration_seconds=300,
    )
    bundle = evaluations.load_claimed_bundle(
        evaluation_id=control.evaluation_id,
        owner="worker-1",
        fencing_epoch=claimed.fencing_epoch,
        source_bundle_digest=claimed.bundle_digest,
    )
    proposal = proposal_for_bundle(bundle)
    grant = _validity_grant(
        db_session,
        ValidityEventType.EVIDENCE_INVALIDATION,
        source_type=ValiditySourceType.EVIDENCE,
        source_id=lineage.evidence_id,
    )
    command = _command(
        db_session,
        source_type=ValiditySourceType.EVIDENCE,
        source_id=lineage.evidence_id,
        event_type=ValidityEventType.EVIDENCE_INVALIDATION,
        authority_id=grant.authority_id,
        key="stale-owner",
    )
    AtomicValidityPropagationService(db_session).execute_propagation(command)
    with pytest.raises(StaleEvaluationOwnerError):
        evaluations.publish_proposal(
            evaluation_id=control.evaluation_id,
            owner="worker-1",
            fencing_epoch=claimed.fencing_epoch,
            source_bundle_digest=claimed.bundle_digest,
            proposal=proposal,
        )


def test_active_retrieval_excludes_invalidated_scientific_state(db_session) -> None:
    seed = _seed_validity_lineage(db_session)
    grant = _validity_grant(
        db_session,
        ValidityEventType.EVIDENCE_INVALIDATION,
        source_type=ValiditySourceType.EVIDENCE,
        source_id=seed["evidence_id"],
    )
    command = _command(
        db_session,
        source_type=ValiditySourceType.EVIDENCE,
        source_id=seed["evidence_id"],
        event_type=ValidityEventType.EVIDENCE_INVALIDATION,
        authority_id=grant.authority_id,
        key="retrieval-exclusion",
    )
    AtomicValidityPropagationService(db_session).execute_propagation(command)
    assert EvidenceRepository(db_session).list(lifecycle_state=EvidenceLifecycleState.ACTIVE) == []
    assert (
        DiscoveryRepository(db_session).list(lifecycle_state=DiscoveryLifecycleState.ACTIVE) == []
    )
    assert SessionFrameRepository(db_session).get_latest_active() is None
    stale_frame = SessionFrameRepository(db_session).get_by_id(seed["session_frame_id"])
    with pytest.raises(ValueError, match="not active"):
        SessionContextBuilder().build(stale_frame, mode=ContextMode.ANSWER)
    result = DiscoveryRetrievalEngine(db_session).retrieve(
        RetrievalRequest(
            objective_id=uuid4(),
            query_text="Tested claim",
            active_data_profile_id=seed["profile_id"],
        )
    )
    assert result.motivation_candidates == []
    assert result.other_relevant_discoveries == []


def test_pre_discovery_source_loss_is_operational_review_not_outcome(db_session) -> None:
    seed = _seed_validity_lineage(db_session, with_discovery=False)
    grant = _validity_grant(
        db_session,
        ValidityEventType.EVIDENCE_INVALIDATION,
        source_type=ValiditySourceType.EVIDENCE,
        source_id=seed["evidence_id"],
    )
    command = _command(
        db_session,
        source_type=ValiditySourceType.EVIDENCE,
        source_id=seed["evidence_id"],
        event_type=ValidityEventType.EVIDENCE_INVALIDATION,
        authority_id=grant.authority_id,
        key="pre-discovery-review",
    )
    AtomicValidityPropagationService(db_session).execute_propagation(command)
    hypothesis = db_session.get(HypothesisRecord, seed["hypothesis_id"])
    task = db_session.get(TaskRecord, seed["task_id"])
    assert hypothesis.status == HypothesisStatus.AWAITING_ADDITIONAL_EVIDENCE
    assert task.lifecycle_state == TaskLifecycleState.ACTIVE
    assert DiscoveryRepository(db_session).list() == []


def test_missing_durable_dependent_rolls_back_source_transition(db_session) -> None:
    seed = _seed_validity_lineage(db_session, with_discovery=False)
    control = db_session.get(EvaluationControlRecord, seed["evaluation_id"])
    control.evidence_ids = [str(seed["evidence_id"]), str(uuid4())]
    db_session.add(control)
    db_session.commit()
    grant = _validity_grant(
        db_session,
        ValidityEventType.EVIDENCE_INVALIDATION,
        source_type=ValiditySourceType.EVIDENCE,
        source_id=seed["evidence_id"],
    )
    command = _command(
        db_session,
        source_type=ValiditySourceType.EVIDENCE,
        source_id=seed["evidence_id"],
        event_type=ValidityEventType.EVIDENCE_INVALIDATION,
        authority_id=grant.authority_id,
        key="missing-dependent",
    )
    with pytest.raises(ValueError, match="missing Evidence"):
        AtomicValidityPropagationService(db_session).execute_propagation(command)
    assert (
        db_session.get(EvidenceRecord, seed["evidence_id"]).lifecycle_state
        == EvidenceLifecycleState.ACTIVE
    )


def test_concurrent_exact_event_has_one_commit_and_one_verified_replay(db_session) -> None:
    seed = _seed_validity_lineage(db_session, with_discovery=False)
    grant = _validity_grant(
        db_session,
        ValidityEventType.EVIDENCE_INVALIDATION,
        source_type=ValiditySourceType.EVIDENCE,
        source_id=seed["evidence_id"],
    )
    command = _command(
        db_session,
        source_type=ValiditySourceType.EVIDENCE,
        source_id=seed["evidence_id"],
        event_type=ValidityEventType.EVIDENCE_INVALIDATION,
        authority_id=grant.authority_id,
        key="concurrent-exact",
    )
    database_url = str(db_session.get_bind().url)
    db_session.close()
    barrier = Barrier(2)

    def execute():
        session = get_session(database_url)
        try:
            barrier.wait()
            return AtomicValidityPropagationService(session).execute_propagation(command)
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [future.result() for future in [pool.submit(execute), pool.submit(execute)]]
    assert sorted(item.replayed for item in results) == [False, True]
    read_session = get_session(database_url)
    try:
        assert len(read_session.exec(text("SELECT event_id FROM validity_events")).all()) == 1
    finally:
        read_session.close()


def test_concurrent_incompatible_events_have_one_winner(db_session) -> None:
    seed = _seed_validity_lineage(db_session, with_discovery=False)
    commands = []
    for event_type in (
        ValidityEventType.EVIDENCE_INVALIDATION,
        ValidityEventType.EVIDENCE_CONFLICT,
    ):
        grant = _validity_grant(
            db_session,
            event_type,
            source_type=ValiditySourceType.EVIDENCE,
            source_id=seed["evidence_id"],
        )
        commands.append(
            _command(
                db_session,
                source_type=ValiditySourceType.EVIDENCE,
                source_id=seed["evidence_id"],
                event_type=event_type,
                authority_id=grant.authority_id,
                key=f"concurrent-incompatible-{event_type.value}",
            )
        )
    database_url = str(db_session.get_bind().url)
    db_session.close()
    barrier = Barrier(2)

    def execute(command):
        session = get_session(database_url)
        try:
            barrier.wait()
            try:
                AtomicValidityPropagationService(session).execute_propagation(command)
                return "committed"
            except StaleValidityPropagationError:
                return "stale"
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(execute, commands))
    assert sorted(results) == ["committed", "stale"]
    read_session = get_session(database_url)
    try:
        assert len(read_session.exec(text("SELECT event_id FROM validity_events")).all()) == 1
    finally:
        read_session.close()


def test_validity_event_migration_quarantines_legacy_rows(tmp_path) -> None:
    database_path = tmp_path / "legacy-validity.sqlite3"
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE validity_events ("
                "event_id CHAR(32) PRIMARY KEY, idempotency_key VARCHAR NOT NULL, "
                "event_fingerprint VARCHAR NOT NULL)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO validity_events VALUES "
                "('00000000000000000000000000000001', 'legacy', 'unverified')"
            )
        )
        connection.execute(
            text("CREATE TABLE analysis_frames (analysis_frame_id CHAR(32) PRIMARY KEY)")
        )
        connection.execute(
            text("INSERT INTO analysis_frames VALUES ('00000000000000000000000000000002')")
        )
    create_db_engine.cache_clear()
    init_db(f"sqlite:///{database_path.as_posix()}")
    table_names = set(
        inspect(create_db_engine(f"sqlite:///{database_path.as_posix()}")).get_table_names()
    )
    assert "validity_events" in table_names
    assert "validity_events_legacy_unverified" in table_names
    with create_db_engine(f"sqlite:///{database_path.as_posix()}").connect() as connection:
        state = connection.execute(text("SELECT validity_state FROM analysis_frames")).scalar_one()
    assert state == ValiditySourceState.UNVERIFIED.name


def test_validity_event_rows_are_database_immutable(db_session) -> None:
    seed = _seed_validity_lineage(db_session, with_discovery=False)
    grant = _validity_grant(
        db_session,
        ValidityEventType.EVIDENCE_INVALIDATION,
        source_type=ValiditySourceType.EVIDENCE,
        source_id=seed["evidence_id"],
    )
    command = _command(
        db_session,
        source_type=ValiditySourceType.EVIDENCE,
        source_id=seed["evidence_id"],
        event_type=ValidityEventType.EVIDENCE_INVALIDATION,
        authority_id=grant.authority_id,
        key="immutable-event",
    )
    result = AtomicValidityPropagationService(db_session).execute_propagation(command)
    event = db_session.get(ValidityEventRecord, result.event_id)
    event.reason = "rewrite"
    db_session.add(event)
    with pytest.raises(IntegrityError, match="validity event is immutable"):
        db_session.commit()
    db_session.rollback()
    with pytest.raises(IntegrityError, match="validity event is immutable"):
        db_session.exec(
            delete(ValidityEventRecord).where(ValidityEventRecord.event_id == result.event_id)
        )
    db_session.rollback()
