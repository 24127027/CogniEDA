"""Real database overlap tests for Package 3 decisions and plan construction."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import UUID

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select, update

from application.discovery import build_discovery_admission_plan
from application.evaluation import EvaluationTransitionService, build_synthesis_bundle
from application.governance import (
    DiscoveryAdmissionGovernanceService,
    ProposalAuthorizationError,
    ProposalDecisionConflictError,
)
from db.migrations import upgrade_proposal_decision_schema
from db.models import (
    DiscoveryRecord,
    EvaluationControlRecord,
    EvidenceRecord,
    GovernanceAuthorityRecord,
    ProposalDecisionRecord,
    SessionFrameRecord,
    utc_now,
)
from db.session import get_session
from package2_helpers import (
    persist_governance_authority,
    persist_package2_lineage,
    proposal_for_bundle,
)
from schemas.enums import (
    DiscoveryEpistemicStatus,
    EvidenceLifecycleState,
    GovernanceDecisionOutcome,
)


def _setup_proposal_ready_evaluation(
    session: Session,
) -> tuple[EvaluationControlRecord, GovernanceAuthorityRecord]:
    lineage = persist_package2_lineage(session)
    evaluation_service = EvaluationTransitionService(session)
    control, _ = evaluation_service.enqueue_evaluation(hypothesis_id=lineage.hypothesis_id)
    claimed = evaluation_service.claim_evaluation(
        evaluation_id=control.evaluation_id,
        owner="system:evaluator",
    )
    bundle, _ = build_synthesis_bundle(session, lineage.hypothesis_id)
    published = evaluation_service.publish_proposal(
        evaluation_id=claimed.evaluation_id,
        owner="system:evaluator",
        fencing_epoch=claimed.fencing_epoch,
        source_bundle_digest=bundle.input_digest,
        proposal=proposal_for_bundle(bundle),
    )
    authority = persist_governance_authority(session)
    return published, authority


def _service(session: Session) -> DiscoveryAdmissionGovernanceService:
    return DiscoveryAdmissionGovernanceService(
        session,
        workspace_id="workspace:test",
        session_id="session:test",
        principal_id="user:lead_researcher",
    )


def test_legacy_decisions_are_quarantined_not_promoted(tmp_path: Path) -> None:
    database_path = (tmp_path / "legacy-decisions.db").as_posix()
    engine = create_engine(f"sqlite:///{database_path}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE proposal_decisions ("
                "decision_id TEXT PRIMARY KEY, evaluation_id TEXT NOT NULL)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO proposal_decisions (decision_id, evaluation_id) "
                "VALUES ('legacy-decision', 'legacy-evaluation')"
            )
        )

    upgrade_proposal_decision_schema(engine)

    table_names = set(inspect(engine).get_table_names())
    assert "proposal_decisions" in table_names
    assert "proposal_decisions_legacy_unverified" in table_names
    with engine.connect() as connection:
        quarantined = connection.execute(
            text("SELECT decision_id FROM proposal_decisions_legacy_unverified")
        ).scalar_one()
        promoted_count = connection.execute(
            text("SELECT COUNT(*) FROM proposal_decisions")
        ).scalar_one()
    assert quarantined == "legacy-decision"
    assert promoted_count == 0


def test_exact_decision_replay_is_idempotent(db_session: Session) -> None:
    published, authority = _setup_proposal_ready_evaluation(db_session)
    service = _service(db_session)
    first = service.record_governance_decision(
        evaluation_id=published.evaluation_id,
        authority_id=authority.authority_id,
        decision=GovernanceDecisionOutcome.APPROVED,
    )
    replay = service.record_governance_decision(
        evaluation_id=published.evaluation_id,
        authority_id=authority.authority_id,
        decision=GovernanceDecisionOutcome.APPROVED,
    )
    assert replay.decision_id == first.decision_id
    assert replay.decision_fingerprint == first.decision_fingerprint

    with pytest.raises(ProposalDecisionConflictError):
        service.record_governance_decision(
            evaluation_id=published.evaluation_id,
            authority_id=authority.authority_id,
            decision=GovernanceDecisionOutcome.REJECTED,
        )


def test_concurrent_approve_approve_returns_one_authoritative_record(
    db_session: Session,
) -> None:
    published, authority = _setup_proposal_ready_evaluation(db_session)
    evaluation_id = published.evaluation_id
    authority_id = authority.authority_id
    database_url = str(db_session.get_bind().url)
    barrier = Barrier(2)

    def approve() -> tuple[str, str]:
        session = get_session(database_url)
        try:
            barrier.wait(timeout=5)
            decision = _service(session).record_governance_decision(
                evaluation_id=evaluation_id,
                authority_id=authority_id,
                decision=GovernanceDecisionOutcome.APPROVED,
            )
            return str(decision.decision_id), decision.decision_fingerprint
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: approve(), range(2)))

    assert len(set(results)) == 1
    db_session.expire_all()
    decisions = db_session.exec(select(ProposalDecisionRecord)).all()
    assert len(decisions) == 1


@pytest.mark.parametrize(
    "competing_outcome",
    [GovernanceDecisionOutcome.REJECTED, GovernanceDecisionOutcome.CANCELLED],
)
def test_concurrent_approve_vs_reject_or_cancel_has_one_authority(
    db_session: Session,
    competing_outcome: GovernanceDecisionOutcome,
) -> None:
    published, authority = _setup_proposal_ready_evaluation(db_session)
    evaluation_id = published.evaluation_id
    authority_id = authority.authority_id
    database_url = str(db_session.get_bind().url)
    barrier = Barrier(2)

    def decide(outcome: GovernanceDecisionOutcome) -> str:
        session = get_session(database_url)
        try:
            barrier.wait(timeout=5)
            try:
                record = _service(session).record_governance_decision(
                    evaluation_id=evaluation_id,
                    authority_id=authority_id,
                    decision=outcome,
                )
                return f"stored:{record.decision.value}"
            except ProposalDecisionConflictError:
                return "conflict"
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                decide,
                (GovernanceDecisionOutcome.APPROVED, competing_outcome),
            )
        )

    assert results.count("conflict") == 1
    assert sum(item.startswith("stored:") for item in results) == 1
    db_session.expire_all()
    decisions = db_session.exec(select(ProposalDecisionRecord)).all()
    assert len(decisions) == 1
    assert decisions[0].decision in {
        GovernanceDecisionOutcome.APPROVED,
        competing_outcome,
    }


@pytest.mark.parametrize("stale_kind", ["proposal", "bundle"])
def test_decision_racing_stale_proposal_or_bundle_cannot_authorize_plan(
    db_session: Session,
    stale_kind: str,
) -> None:
    published, authority = _setup_proposal_ready_evaluation(db_session)
    evaluation_id = published.evaluation_id
    authority_id = authority.authority_id
    evidence_id = UUID(published.evidence_ids[0])
    database_url = str(db_session.get_bind().url)
    barrier = Barrier(2)

    def decide() -> str:
        session = get_session(database_url)
        try:
            barrier.wait(timeout=5)
            try:
                record = _service(session).record_governance_decision(
                    evaluation_id=evaluation_id,
                    authority_id=authority_id,
                    decision=GovernanceDecisionOutcome.APPROVED,
                )
                return str(record.decision_id)
            except ProposalAuthorizationError:
                return "stale"
        finally:
            session.close()

    def make_stale() -> None:
        session = get_session(database_url)
        try:
            barrier.wait(timeout=5)
            if stale_kind == "proposal":
                session.execute(
                    update(EvaluationControlRecord)
                    .where(EvaluationControlRecord.evaluation_id == evaluation_id)
                    .values(proposal_digest="stale-proposal")
                )
            else:
                evidence = session.get(EvidenceRecord, evidence_id)
                assert evidence is not None
                evidence.lifecycle_state = EvidenceLifecycleState.INVALIDATED
                session.add(evidence)
            session.commit()
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        decision_future = pool.submit(decide)
        stale_future = pool.submit(make_stale)
        decision_result = decision_future.result()
        stale_future.result()

    if decision_result != "stale":
        with pytest.raises(ProposalAuthorizationError):
            build_discovery_admission_plan(
                db_session,
                evaluation_id,
                decision_result,
                workspace_id="workspace:test",
                session_id="session:test",
            )


def test_concurrent_plan_reuse_is_identical_read_only_and_unconsumed(
    db_session: Session,
) -> None:
    published, authority = _setup_proposal_ready_evaluation(db_session)
    decision = _service(db_session).record_governance_decision(
        evaluation_id=published.evaluation_id,
        authority_id=authority.authority_id,
        decision=GovernanceDecisionOutcome.APPROVED,
    )
    evaluation_id = published.evaluation_id
    decision_id = decision.decision_id
    database_url = str(db_session.get_bind().url)
    barrier = Barrier(2)

    def construct_plan() -> tuple[str, str]:
        session = get_session(database_url)
        try:
            barrier.wait(timeout=5)
            plan = build_discovery_admission_plan(
                session,
                evaluation_id,
                decision_id,
                workspace_id="workspace:test",
                session_id="session:test",
            )
            return str(plan.deterministic_discovery_id), plan.admission_fingerprint
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: construct_plan(), range(2)))

    assert len(set(results)) == 1
    db_session.expire_all()
    stored = db_session.get(ProposalDecisionRecord, decision_id)
    assert stored is not None and stored.consumed is False
    assert db_session.exec(select(DiscoveryRecord)).all() == []
    assert db_session.exec(select(SessionFrameRecord)).all() == []


def test_decision_core_is_immutable_and_consumption_requires_committed_chain(
    db_session: Session,
) -> None:
    published, authority = _setup_proposal_ready_evaluation(db_session)
    decision = _service(db_session).record_governance_decision(
        evaluation_id=published.evaluation_id,
        authority_id=authority.authority_id,
        decision=GovernanceDecisionOutcome.APPROVED,
    )

    with pytest.raises(IntegrityError):
        db_session.execute(
            update(ProposalDecisionRecord)
            .where(ProposalDecisionRecord.decision_id == decision.decision_id)
            .values(reason="tampered")
        )
        db_session.commit()
    db_session.rollback()

    with pytest.raises(IntegrityError, match="exact committed chain"):
        db_session.execute(
            update(ProposalDecisionRecord)
            .where(ProposalDecisionRecord.decision_id == decision.decision_id)
            .values(
                consumed=True,
                consumed_at=utc_now(),
                consumed_by="detached-discovery",
            )
        )
        db_session.commit()
    db_session.rollback()
    db_session.refresh(decision)
    assert decision.consumed is False


def test_governance_authority_core_and_expiry_are_immutable(db_session: Session) -> None:
    _, authority = _setup_proposal_ready_evaluation(db_session)

    with pytest.raises(IntegrityError, match="authority core is immutable"):
        db_session.execute(
            update(GovernanceAuthorityRecord)
            .where(GovernanceAuthorityRecord.authority_id == authority.authority_id)
            .values(expires_at=utc_now())
        )
        db_session.commit()
    db_session.rollback()


def test_existing_discovery_racing_plan_never_gets_overwritten(db_session: Session) -> None:
    published, authority = _setup_proposal_ready_evaluation(db_session)
    decision = _service(db_session).record_governance_decision(
        evaluation_id=published.evaluation_id,
        authority_id=authority.authority_id,
        decision=GovernanceDecisionOutcome.APPROVED,
    )
    evaluation_id = published.evaluation_id
    decision_id = decision.decision_id
    hypothesis_id = published.hypothesis_id
    evidence_ids = list(published.evidence_ids)
    database_url = str(db_session.get_bind().url)
    barrier = Barrier(2)

    def construct() -> str:
        session = get_session(database_url)
        try:
            barrier.wait(timeout=5)
            try:
                return (
                    build_discovery_admission_plan(
                        session,
                        evaluation_id,
                        decision_id,
                        workspace_id="workspace:test",
                        session_id="session:test",
                    )
                    .admission_fingerprint
                )
            except ProposalAuthorizationError:
                return "blocked"
        finally:
            session.close()

    def insert_discovery() -> None:
        session = get_session(database_url)
        try:
            barrier.wait(timeout=5)
            session.add(
                DiscoveryRecord(
                    hypothesis_id=hypothesis_id,
                    evidence_ids=evidence_ids,
                    claim={"statement": "Concurrent pre-existing claim"},
                    epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
                    scope="bounded",
                    validity_basis={},
                    invalidators=[],
                )
            )
            session.commit()
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        plan_future = pool.submit(construct)
        discovery_future = pool.submit(insert_discovery)
        plan_result = plan_future.result()
        discovery_future.result()

    assert plan_result == "blocked" or len(plan_result) == 64
    db_session.expire_all()
    discoveries = db_session.exec(select(DiscoveryRecord)).all()
    assert len(discoveries) == 1
    with pytest.raises(ProposalAuthorizationError):
        _service(db_session).verify_authorization(
            evaluation_id,
            decision_id,
        )
