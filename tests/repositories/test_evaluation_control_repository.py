"""Real transaction, CAS, idempotency, and recovery tests for evaluation control."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest

from application.orchestrator.evaluation_transition_service import (
    EvaluationConflictError,
    EvaluationTransitionError,
    EvaluationTransitionService,
    StaleEvaluationOwnerError,
)
from application.orchestrator.synthesis_bundle import build_synthesis_bundle
from db.models import EvaluationControlRecord, HypothesisRecord, utc_now
from db.session import get_session
from package2_helpers import (
    persist_package2_lineage,
    propagate_validity_for_test,
    proposal_for_bundle,
)
from repositories.evaluation_control_repository import EvaluationControlRepository
from schemas.enums import (
    EvaluationControlState,
    HypothesisStatus,
    ValidityEventType,
    ValiditySourceType,
)
from schemas.specialist_contracts import EvaluationFailure, EvaluationFailureReason


def test_enqueue_is_identity_bound_and_exact_replay_is_idempotent(db_session) -> None:
    lineage = persist_package2_lineage(db_session)
    service = EvaluationTransitionService(db_session)

    first, created = service.enqueue_evaluation(hypothesis_id=lineage.hypothesis_id)
    replay, replay_created = service.enqueue_evaluation(hypothesis_id=lineage.hypothesis_id)

    assert created is True
    assert replay_created is False
    assert replay.evaluation_id == first.evaluation_id
    assert first.state == EvaluationControlState.PENDING
    assert first.fencing_epoch == 0
    assert first.evaluation_key
    assert first.evidence_set_digest
    assert first.serialized_manifest


def test_source_loss_invalidates_control_and_requires_successor_hypothesis_lineage(
    db_session,
) -> None:
    lineage = persist_package2_lineage(db_session)
    service = EvaluationTransitionService(db_session)
    first, _ = service.enqueue_evaluation(hypothesis_id=lineage.hypothesis_id)
    propagate_validity_for_test(
        db_session,
        source_type=ValiditySourceType.EVIDENCE,
        source_id=lineage.evidence_id,
        event_type=ValidityEventType.EVIDENCE_INVALIDATION,
        reason="Superseded by corrected admitted observation.",
        idempotency_key="changed-evidence-set",
    )
    db_session.refresh(first)
    assert first.state == EvaluationControlState.INVALIDATED
    hypothesis = db_session.get(HypothesisRecord, lineage.hypothesis_id)
    assert hypothesis.status == HypothesisStatus.AWAITING_ADDITIONAL_EVIDENCE
    with pytest.raises(ValueError, match="READY_FOR_EVALUATION"):
        service.enqueue_evaluation(hypothesis_id=lineage.hypothesis_id)


def test_concurrent_enqueue_and_claim_each_have_one_winner(db_session) -> None:
    lineage = persist_package2_lineage(db_session)
    database_url = str(db_session.get_bind().url)
    enqueue_barrier = Barrier(2)

    def enqueue() -> tuple[str, bool]:
        session = get_session(database_url)
        try:
            enqueue_barrier.wait()
            record, created = EvaluationTransitionService(session).enqueue_evaluation(
                hypothesis_id=lineage.hypothesis_id
            )
            return str(record.evaluation_id), created
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        enqueue_results = list(pool.map(lambda _: enqueue(), range(2)))
    assert len({result[0] for result in enqueue_results}) == 1
    assert sorted(result[1] for result in enqueue_results) == [False, True]

    evaluation_id = (
        EvaluationControlRepository(db_session)
        .list_by_hypothesis(lineage.hypothesis_id)[0]
        .evaluation_id
    )
    claim_barrier = Barrier(2)

    def claim(owner: str) -> str:
        session = get_session(database_url)
        try:
            claim_barrier.wait()
            try:
                EvaluationTransitionService(session).claim_evaluation(
                    evaluation_id=evaluation_id,
                    owner=owner,
                )
                return "won"
            except EvaluationTransitionError:
                return "lost"
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        claim_results = list(pool.map(claim, ("worker-a", "worker-b")))
    assert sorted(claim_results) == ["lost", "won"]


def test_expired_claim_reclaim_fences_stale_owner_publication(db_session) -> None:
    lineage = persist_package2_lineage(db_session)
    service = EvaluationTransitionService(db_session)
    record, _ = service.enqueue_evaluation(hypothesis_id=lineage.hypothesis_id)
    first = service.claim_evaluation(evaluation_id=record.evaluation_id, owner="worker-a")
    first.claim_expiry = utc_now() - timedelta(seconds=1)
    db_session.add(first)
    db_session.commit()

    second = service.claim_evaluation(evaluation_id=record.evaluation_id, owner="worker-b")
    bundle, _ = build_synthesis_bundle(db_session, lineage.hypothesis_id)
    proposal = proposal_for_bundle(bundle)

    with pytest.raises(StaleEvaluationOwnerError):
        service.publish_proposal(
            evaluation_id=record.evaluation_id,
            owner="worker-a",
            fencing_epoch=first.fencing_epoch,
            source_bundle_digest=bundle.input_digest,
            proposal=proposal,
        )
    published = service.publish_proposal(
        evaluation_id=record.evaluation_id,
        owner="worker-b",
        fencing_epoch=second.fencing_epoch,
        source_bundle_digest=bundle.input_digest,
        proposal=proposal,
    )
    assert published.state == EvaluationControlState.PROPOSAL_READY


def test_expired_claim_cannot_publish_failure(db_session) -> None:
    lineage = persist_package2_lineage(db_session)
    service = EvaluationTransitionService(db_session)
    record, _ = service.enqueue_evaluation(hypothesis_id=lineage.hypothesis_id)
    claimed = service.claim_evaluation(evaluation_id=record.evaluation_id, owner="worker")
    claimed.claim_expiry = utc_now() - timedelta(seconds=1)
    db_session.add(claimed)
    db_session.commit()

    with pytest.raises(StaleEvaluationOwnerError):
        service.record_failure(
            evaluation_id=record.evaluation_id,
            owner="worker",
            fencing_epoch=claimed.fencing_epoch,
            source_bundle_digest=claimed.bundle_digest,
            failure=EvaluationFailure(
                failure_reason=EvaluationFailureReason.TRANSIENT_PROVIDER_FAILURE,
                message="Provider timeout.",
            ),
            retryable=True,
        )


def test_concurrent_changed_proposals_cannot_both_publish(db_session) -> None:
    lineage = persist_package2_lineage(db_session)
    bundle, _ = build_synthesis_bundle(db_session, lineage.hypothesis_id)
    first_proposal = proposal_for_bundle(bundle)
    second_proposal = first_proposal.model_copy(
        update={
            "claim": first_proposal.claim.model_copy(
                update={"result": "A distinct, still evidence-bound interpretation."}
            )
        }
    )
    service = EvaluationTransitionService(db_session)
    record, _ = service.enqueue_evaluation(hypothesis_id=lineage.hypothesis_id)
    claimed = service.claim_evaluation(evaluation_id=record.evaluation_id, owner="worker")
    database_url = str(db_session.get_bind().url)
    publish_barrier = Barrier(2)

    def publish(proposal) -> str:
        session = get_session(database_url)
        try:
            publish_barrier.wait()
            try:
                EvaluationTransitionService(session).publish_proposal(
                    evaluation_id=record.evaluation_id,
                    owner="worker",
                    fencing_epoch=claimed.fencing_epoch,
                    source_bundle_digest=bundle.input_digest,
                    proposal=proposal,
                )
                return "published"
            except EvaluationConflictError:
                return "conflict"
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(publish, (first_proposal, second_proposal)))

    assert sorted(results) == ["conflict", "published"]
    db_session.expire_all()
    final = db_session.get(EvaluationControlRecord, record.evaluation_id)
    assert final is not None
    assert final.state == EvaluationControlState.CONFLICT


def test_retryable_failure_retries_same_bundle_and_attempt_number(db_session) -> None:
    lineage = persist_package2_lineage(db_session)
    service = EvaluationTransitionService(db_session)
    record, _ = service.enqueue_evaluation(hypothesis_id=lineage.hypothesis_id)
    claimed = service.claim_evaluation(evaluation_id=record.evaluation_id, owner="worker")
    failure = EvaluationFailure(
        failure_reason=EvaluationFailureReason.TRANSIENT_PROVIDER_FAILURE,
        message="Provider timeout.",
    )
    failed = service.record_failure(
        evaluation_id=record.evaluation_id,
        owner="worker",
        fencing_epoch=claimed.fencing_epoch,
        source_bundle_digest=claimed.bundle_digest,
        failure=failure,
        retryable=True,
    )
    assert failed.state == EvaluationControlState.RETRYABLE_FAILED
    assert failed.serialized_failure == failure.model_dump(mode="json")

    retried = service.retry_evaluation(evaluation_id=record.evaluation_id)
    assert retried.state == EvaluationControlState.PENDING
    assert retried.attempt_number == 2
    assert retried.bundle_digest == claimed.bundle_digest


def test_partial_identity_replay_is_quarantined_not_accepted(db_session) -> None:
    lineage = persist_package2_lineage(db_session)
    service = EvaluationTransitionService(db_session)
    record, _ = service.enqueue_evaluation(hypothesis_id=lineage.hypothesis_id)
    record.serialized_manifest = {}
    db_session.add(record)
    db_session.commit()

    with pytest.raises(EvaluationConflictError, match="partial or conflicting"):
        service.enqueue_evaluation(hypothesis_id=lineage.hypothesis_id)
    db_session.refresh(record)
    assert record.state == EvaluationControlState.CONFLICT


def test_partial_terminal_identity_is_quarantined_not_replayed(db_session) -> None:
    lineage = persist_package2_lineage(db_session)
    service = EvaluationTransitionService(db_session)
    record, _ = service.enqueue_evaluation(hypothesis_id=lineage.hypothesis_id)
    record.state = EvaluationControlState.NON_RETRYABLE_FAILED
    record.serialized_manifest = {}
    db_session.add(record)
    db_session.commit()

    with pytest.raises(EvaluationConflictError, match="partial or conflicting"):
        service.enqueue_evaluation(hypothesis_id=lineage.hypothesis_id)
    db_session.refresh(record)
    assert record.state == EvaluationControlState.CONFLICT


def test_repository_stage_create_does_not_self_commit(db_session) -> None:
    lineage = persist_package2_lineage(db_session)
    bundle, manifest = build_synthesis_bundle(db_session, lineage.hypothesis_id)
    record = EvaluationControlRecord(
        hypothesis_id=lineage.hypothesis_id,
        evidence_ids=[str(lineage.evidence_id)],
        evidence_set_digest="e" * 64,
        bundle_digest=bundle.input_digest,
        contract_version=bundle.contract_version,
        evaluation_key="k" * 64,
        serialized_manifest=manifest.model_dump(mode="json"),
    )
    EvaluationControlRepository(db_session).stage_create(record)
    db_session.rollback()
    assert db_session.get(EvaluationControlRecord, record.evaluation_id) is None
