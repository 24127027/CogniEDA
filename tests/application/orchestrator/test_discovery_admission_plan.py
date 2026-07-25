"""Phase B DiscoveryAdmissionPlan tests for Package 3."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlmodel import Session

from application.evaluation import EvaluationTransitionService, build_synthesis_bundle
from application.governance import (
    DiscoveryAdmissionGovernanceService,
    compute_admission_fingerprint,
    generate_deterministic_discovery_id,
)
from db.models import EvaluationControlRecord
from package2_helpers import (
    persist_governance_authority,
    persist_package2_lineage,
    proposal_for_bundle,
)
from schemas.discovery_admission_contracts import DiscoveryAdmissionPlan
from schemas.enums import (
    DiscoveryEpistemicStatus,
    EvaluationControlState,
    GovernanceDecisionOutcome,
    HypothesisStatus,
    TaskLifecycleState,
)


def _setup_proposal_ready_evaluation(
    session: Session,
    *,
    epistemic_status: DiscoveryEpistemicStatus = DiscoveryEpistemicStatus.SUPPORTED,
) -> tuple[EvaluationControlRecord, DiscoveryAdmissionGovernanceService, object]:
    lineage = persist_package2_lineage(session)
    service = EvaluationTransitionService(session)
    control_record, _ = service.enqueue_evaluation(hypothesis_id=lineage.hypothesis_id)
    claimed = service.claim_evaluation(
        evaluation_id=control_record.evaluation_id, owner="system:evaluator"
    )

    bundle, _ = build_synthesis_bundle(session, lineage.hypothesis_id)
    proposal = proposal_for_bundle(bundle, epistemic_status=epistemic_status)
    published = service.publish_proposal(
        evaluation_id=claimed.evaluation_id,
        owner="system:evaluator",
        fencing_epoch=claimed.fencing_epoch,
        source_bundle_digest=bundle.input_digest,
        proposal=proposal,
    )

    authority = persist_governance_authority(session)
    gov_service = DiscoveryAdmissionGovernanceService(
        session,
        workspace_id="workspace:test",
        session_id="session:test",
    )
    return published, gov_service, authority


def test_valid_proposal_creates_one_deterministic_frozen_plan(db_session: Session) -> None:
    published, gov_service, authority = _setup_proposal_ready_evaluation(db_session)

    decision_rec = gov_service.record_governance_decision(
        evaluation_id=published.evaluation_id,
        authority_id=authority.authority_id,
        decision=GovernanceDecisionOutcome.APPROVED,
    )

    plan = gov_service.create_admission_plan(published.evaluation_id, decision_rec.decision_id)

    assert isinstance(plan, DiscoveryAdmissionPlan)
    assert plan.evaluation_id == published.evaluation_id
    assert plan.proposal_digest == published.proposal_digest
    assert plan.hypothesis_id == published.hypothesis_id
    assert plan.expected_evaluation_state == EvaluationControlState.PROPOSAL_READY
    assert plan.expected_hypothesis_state == HypothesisStatus.READY_FOR_EVALUATION
    assert plan.expected_task_state == TaskLifecycleState.ACTIVE
    assert len(plan.future_atomic_write_set.write_operations) == 7
    assert plan.authorization_authority_id == authority.authority_id
    assert plan.evaluation_key == published.evaluation_key
    assert plan.evidence_set_digest == published.evidence_set_digest
    assert plan.analysis_frame_ids

    # Immutability check: the plan and nested scientific snapshots are frozen.
    with pytest.raises(ValidationError):
        plan.proposal_digest = "tampered"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        plan.proposed_claim.statement = "tampered"  # type: ignore[misc]


def test_exact_proposal_replay_creates_same_plan_and_id(db_session: Session) -> None:
    published, gov_service, authority = _setup_proposal_ready_evaluation(db_session)

    decision_rec = gov_service.record_governance_decision(
        evaluation_id=published.evaluation_id,
        authority_id=authority.authority_id,
        decision=GovernanceDecisionOutcome.APPROVED,
    )

    plan1 = gov_service.create_admission_plan(published.evaluation_id, decision_rec.decision_id)
    plan2 = gov_service.create_admission_plan(published.evaluation_id, decision_rec.decision_id)

    assert plan1 == plan2
    assert plan1.deterministic_discovery_id == plan2.deterministic_discovery_id
    assert plan1.admission_fingerprint == plan2.admission_fingerprint

    # Verify deterministic Discovery ID derivation formula
    expected_id = generate_deterministic_discovery_id(
        published.hypothesis_id, published.proposal_digest
    )
    assert plan1.deterministic_discovery_id == expected_id


def test_admission_fingerprint_covers_scientific_and_authorization_identity(
    db_session: Session,
) -> None:
    published, gov_service, authority = _setup_proposal_ready_evaluation(db_session)
    decision = gov_service.record_governance_decision(
        evaluation_id=published.evaluation_id,
        authority_id=authority.authority_id,
        decision=GovernanceDecisionOutcome.APPROVED,
    )
    plan = gov_service.create_admission_plan(published.evaluation_id, decision.decision_id)

    scientific_change = plan.model_copy(
        update={
            "proposed_claim": plan.proposed_claim.model_copy(
                update={"statement": "Scientifically different claim."}
            )
        }
    )
    authorization_change = plan.model_copy(update={"authorization_decision_id": uuid4()})

    assert compute_admission_fingerprint(scientific_change) != plan.admission_fingerprint
    assert compute_admission_fingerprint(authorization_change) != plan.admission_fingerprint
    assert scientific_change.deterministic_discovery_id == plan.deterministic_discovery_id


@pytest.mark.parametrize(
    "epistemic_status",
    [
        DiscoveryEpistemicStatus.SUPPORTED,
        DiscoveryEpistemicStatus.CONTRADICTED,
        DiscoveryEpistemicStatus.INCONCLUSIVE,
        DiscoveryEpistemicStatus.INSUFFICIENT_EVIDENCE,
    ],
)
def test_all_four_epistemic_outcomes_accepted(
    db_session: Session, epistemic_status: DiscoveryEpistemicStatus
) -> None:
    published, gov_service, authority = _setup_proposal_ready_evaluation(
        db_session, epistemic_status=epistemic_status
    )

    decision_rec = gov_service.record_governance_decision(
        evaluation_id=published.evaluation_id,
        authority_id=authority.authority_id,
        decision=GovernanceDecisionOutcome.APPROVED,
    )

    plan = gov_service.create_admission_plan(published.evaluation_id, decision_rec.decision_id)
    assert plan.epistemic_status == epistemic_status


def test_scientific_meaning_preservation(db_session: Session) -> None:
    published, gov_service, authority = _setup_proposal_ready_evaluation(db_session)

    decision_rec = gov_service.record_governance_decision(
        evaluation_id=published.evaluation_id,
        authority_id=authority.authority_id,
        decision=GovernanceDecisionOutcome.APPROVED,
    )

    plan = gov_service.create_admission_plan(published.evaluation_id, decision_rec.decision_id)

    raw_proposal = published.serialized_proposal
    assert raw_proposal is not None
    assert plan.proposed_claim.model_dump(mode="json") == raw_proposal["claim"]
    assert plan.scope == raw_proposal["scope"]
    frozen_basis = plan.validity_basis.model_dump(
        mode="json",
        exclude={"decision_rule"},
    )
    raw_basis = {
        key: value
        for key, value in raw_proposal["validity_basis"].items()
        if key != "decision_rule"
    }
    assert frozen_basis == raw_basis
    assert (
        plan.validity_basis.decision_rule.to_domain().model_dump(mode="json")
        == raw_proposal["validity_basis"]["decision_rule"]
    )
    assert plan.uncertainty == raw_proposal["validity_basis"]["uncertainty"]
