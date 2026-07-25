"""Repository tests for Discovery and DiscoveryAdmissionClaim repositories."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlmodel import Session

from db.init_db import init_db
from db.models import (
    DataProfileRecord,
    EvaluationControlRecord,
    GovernanceAuthorityRecord,
    HypothesisRecord,
    ProposalDecisionRecord,
    TaskRecord,
)
from db.session import create_db_engine
from repositories.discovery import DiscoveryAdmissionClaimRepository, DiscoveryRepository
from schemas.enums import (
    AuthorizationClass,
    EvaluationControlState,
    GovernanceDecisionOutcome,
    HypothesisStatus,
    TaskKind,
    TaskLifecycleState,
)


@pytest.fixture
def session() -> Session:
    engine = create_db_engine("sqlite:///:memory:")
    init_db("sqlite:///:memory:")
    with Session(engine) as sess:
        yield sess


def test_discovery_repository_rejects_generic_create(session: Session) -> None:
    repo = DiscoveryRepository(session)
    with pytest.raises(RuntimeError, match="owned by AtomicDiscoveryAdmissionService"):
        repo.create(None)  # type: ignore[arg-type]


def test_discovery_admission_claim_repository_get_by_id(session: Session) -> None:
    repo = DiscoveryAdmissionClaimRepository(session)

    # Seed required FK lineage
    profile = DataProfileRecord(
        profile_id=uuid4(),
        dataset_path="data.csv",
        schema_summary={"column_order": ["x"]},
        baseline_summary={"column_names": ["x"]},
        row_count=10,
        column_count=1,
        method="baseline_summary",
    )
    session.add(profile)
    session.flush()

    task = TaskRecord(
        task_id=uuid4(),
        profile_id=profile.profile_id,
        title="Task",
        description="Desc",
        variables=["x"],
        task_kind=TaskKind.ANALYTICAL,
        lifecycle_state=TaskLifecycleState.ACTIVE,
    )
    session.add(task)
    session.flush()

    hypothesis = HypothesisRecord(
        hypothesis_id=uuid4(),
        task_id=task.task_id,
        profile_id=profile.profile_id,
        statement="Statement",
        variables=["x"],
        scope="scope",
        validation_method="method",
        evidence_expectation="exp",
        status=HypothesisStatus.READY_FOR_EVALUATION,
    )
    session.add(hypothesis)
    session.flush()

    eval_control = EvaluationControlRecord(
        evaluation_id=uuid4(),
        hypothesis_id=hypothesis.hypothesis_id,
        evidence_ids=["ev-1"],
        evidence_set_digest="ev-digest",
        bundle_digest="bundle-digest",
        contract_version="1.0",
        evaluation_key="eval-key-1",
        state=EvaluationControlState.PENDING,
    )
    session.add(eval_control)
    session.flush()

    authority = GovernanceAuthorityRecord(
        authority_id=uuid4(),
        actor_identity="user-1",
        authority_class=AuthorizationClass.USER_GOVERNED,
        workspace_id="ws-1",
        session_id="sess-1",
        purpose="evaluation",
        operation_type="approve",
        issued_by="system",
        authority_fingerprint="fp-auth-1",
    )
    session.add(authority)
    session.flush()

    decision = ProposalDecisionRecord(
        decision_id=uuid4(),
        authority_id=authority.authority_id,
        evaluation_id=eval_control.evaluation_id,
        evaluation_key=eval_control.evaluation_key,
        hypothesis_id=hypothesis.hypothesis_id,
        task_id=task.task_id,
        proposal_digest="prop-digest",
        bundle_digest="bundle-digest",
        evidence_set_digest="ev-digest",
        decision=GovernanceDecisionOutcome.APPROVED,
        actor="user-1",
        actor_authority_type=AuthorizationClass.USER_GOVERNED,
        workspace_id="ws-1",
        purpose="evaluation",
        operation_type="approve",
        decision_fingerprint="fp-dec-1",
    )
    session.add(decision)
    session.flush()

    claim = repo._stage_enqueue_from_atomic_admission(
        evaluation_id=eval_control.evaluation_id,
        decision_id=decision.decision_id,
        proposal_digest="prop-digest",
        bundle_digest="bundle-digest",
        admission_fingerprint="fp-adm-1",
    )
    session.flush()

    found = repo.get_by_id(claim.claim_id)
    assert found is not None
    assert found.evaluation_id == eval_control.evaluation_id
    assert found.decision_id == decision.decision_id
