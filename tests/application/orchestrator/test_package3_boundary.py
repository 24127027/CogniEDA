"""Boundary verification tests for Package 3 non-execution of durable cutover."""

from __future__ import annotations

from sqlmodel import Session, select

from application.discovery import build_discovery_admission_plan
from application.evaluation import EvaluationTransitionService, build_synthesis_bundle
from application.governance import (
    DiscoveryAdmissionGovernanceService,
)
from db.models import (
    DiscoveryRecord,
    EvaluationControlRecord,
    HypothesisRecord,
    ProposalDecisionRecord,
    SessionFrameRecord,
    TaskRecord,
)
from package2_helpers import (
    persist_governance_authority,
    persist_package2_lineage,
    proposal_for_bundle,
)
from schemas.enums import (
    EvaluationControlState,
    GovernanceDecisionOutcome,
    HypothesisStatus,
    TaskLifecycleState,
)


def test_package3_boundary_invariants(db_session: Session) -> None:
    lineage = persist_package2_lineage(db_session)
    service = EvaluationTransitionService(db_session)
    control_record, _ = service.enqueue_evaluation(hypothesis_id=lineage.hypothesis_id)
    claimed = service.claim_evaluation(
        evaluation_id=control_record.evaluation_id, owner="system:evaluator"
    )

    bundle, _ = build_synthesis_bundle(db_session, lineage.hypothesis_id)
    proposal = proposal_for_bundle(bundle)
    published = service.publish_proposal(
        evaluation_id=claimed.evaluation_id,
        owner="system:evaluator",
        fencing_epoch=claimed.fencing_epoch,
        source_bundle_digest=bundle.input_digest,
        proposal=proposal,
    )

    authority = persist_governance_authority(db_session)
    gov_service = DiscoveryAdmissionGovernanceService(
        db_session,
        workspace_id="workspace:test",
        session_id="session:test",
        principal_id="user:lead_researcher",
    )
    decision_rec = gov_service.record_governance_decision(
        evaluation_id=published.evaluation_id,
        authority_id=authority.authority_id,
        decision=GovernanceDecisionOutcome.APPROVED,
    )

    # Construct admission plan
    build_discovery_admission_plan(
        db_session,
        published.evaluation_id,
        decision_rec.decision_id,
        workspace_id="workspace:test",
        session_id="session:test",
    )

    # 1. Package 3 writes NO DiscoveryRecord
    discoveries = db_session.exec(select(DiscoveryRecord)).all()
    assert len(discoveries) == 0

    # 2. Hypothesis remains READY_FOR_EVALUATION
    hyp = db_session.get(HypothesisRecord, published.hypothesis_id)
    assert hyp is not None and hyp.status == HypothesisStatus.READY_FOR_EVALUATION

    # 3. Task remains ACTIVE
    task = db_session.get(TaskRecord, lineage.task_id)
    assert task is not None and task.lifecycle_state == TaskLifecycleState.ACTIVE

    # 4. EvaluationControlRecord remains PROPOSAL_READY
    eval_rec = db_session.get(EvaluationControlRecord, published.evaluation_id)
    assert eval_rec is not None and eval_rec.state == EvaluationControlState.PROPOSAL_READY

    # 5. Decision is NOT consumed merely by plan construction
    dec_rec = db_session.get(ProposalDecisionRecord, decision_rec.decision_id)
    assert dec_rec is not None and dec_rec.consumed is False

    # 6. No conclusion SessionFrame written
    db_session_frames = db_session.exec(select(SessionFrameRecord)).all()
    assert len(db_session_frames) == 0
