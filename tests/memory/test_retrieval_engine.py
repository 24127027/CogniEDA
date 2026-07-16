from uuid import uuid4

import pytest
from sqlmodel import Session

from db.models import TaskRecord
from memory.retrieval_engine import DiscoveryRetrievalEngine
from memory.semantic_scorer import LexicalScorer
from schemas.artifacts import Discovery, Objective, SessionFrame, Task
from schemas.common import DiscoveryClaim, ValidityBasis
from schemas.enums import (
    DiscoveryEpistemicStatus,
    DiscoveryLifecycleState,
)
from schemas.retrieval import RetrievalRequest


@pytest.fixture
def mock_objective() -> Objective:
    return Objective(
        objective_id=uuid4(),
        title="Test Objective",
        statement="Test Objective Statement",
    )


@pytest.fixture
def create_validity(db_session: Session):
    def _create_validity() -> ValidityBasis:
        from db.models import DataProfileRecord, EvidenceRecord, HypothesisRecord
        from schemas.enums import EvidenceType

        profile_id = uuid4()
        task_id = uuid4()
        hypothesis_id = uuid4()
        evidence_id = uuid4()

        db_session.add(
            DataProfileRecord(
                profile_id=profile_id, dataset_path="p", method="m", row_count=1, column_count=1
            )
        )
        db_session.add(
            TaskRecord(task_id=task_id, title="T", description="D", profile_id=profile_id)
        )
        db_session.flush()
        db_session.add(
            HypothesisRecord(
                hypothesis_id=hypothesis_id,
                task_id=task_id,
                profile_id=profile_id,
                statement="H",
                scope="S",
                validation_method="V",
                evidence_expectation="E",
            )
        )
        db_session.flush()
        db_session.add(
            EvidenceRecord(
                evidence_id=evidence_id,
                hypothesis_id=hypothesis_id,
                profile_id=profile_id,
                analysis_frame_ref="test_ref",
                execution_run_ref="execution-run:001",
                evidence_type=EvidenceType.SUMMARY_STATISTIC,
                method="test_method",
                parameters=[],
                provenance={},
                result_summary={},
                artifact_refs=[],
                limitations=[],
            )
        )
        db_session.commit()

        return ValidityBasis(
            hypothesis_id=hypothesis_id,
            evidence_ids=[evidence_id],
            assumptions_excluded_from_inference=True,
            data_profile_id=profile_id,
            analysis_frame_refs=[],
            method="Test Method",
            decision_rule={},
        )

    return _create_validity


def test_retrieval_separates_motivation_from_context(db_session: Session, create_validity) -> None:
    v1 = create_validity()
    v2 = create_validity()

    # Setup
    parent_task = Task(
        task_id=uuid4(),
        title="Parent Task",
        description="Parent desc",
        variables=["X"],
    )
    direct_motivation = Discovery(
        discovery_id=uuid4(),
        hypothesis_id=v1.hypothesis_id,
        evidence_ids=v1.evidence_ids,
        claim=DiscoveryClaim(statement="Direct claim", scope="Global"),
        epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
        scope="Global",
        validity_basis=v1,
    )
    parent_task.motivated_by_discovery_ids = [direct_motivation.discovery_id]

    other_discovery = Discovery(
        discovery_id=uuid4(),
        hypothesis_id=v2.hypothesis_id,
        evidence_ids=v2.evidence_ids,
        claim=DiscoveryClaim(statement="Other relevant claim", scope="Global"),
        epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
        scope="Global",
        validity_basis=v2,
    )

    from repositories.discovery_repository import DiscoveryRepository
    from repositories.task_repository import TaskRepository

    DiscoveryRepository(db_session).create(direct_motivation)
    DiscoveryRepository(db_session).create(other_discovery)
    TaskRepository(db_session).create(parent_task)

    engine = DiscoveryRetrievalEngine(db_session)
    request = RetrievalRequest(
        objective_id=uuid4(),
        parent_task_id=parent_task.task_id,
        query_text="relevant claim",
    )

    # Execute
    result = engine.retrieve(request, None)

    # Assert
    assert len(result.motivation_candidates) == 2
    assert len(result.other_relevant_discoveries) == 0

    motivation_ids = {c.discovery_id for c in result.motivation_candidates}
    assert direct_motivation.discovery_id in motivation_ids
    assert other_discovery.discovery_id in motivation_ids


def test_retrieval_ranks_by_structural_relations(db_session: Session, create_validity) -> None:
    v1 = create_validity()
    v2 = create_validity()
    v3 = create_validity()

    ancestor_task = Task(task_id=uuid4(), title="Ancestor", description="Desc", variables=["X"])
    parent_task = Task(
        task_id=uuid4(),
        title="Parent",
        description="Desc",
        variables=["X"],
        parent_task_id=ancestor_task.task_id,
    )

    d_direct = Discovery(
        discovery_id=uuid4(),
        hypothesis_id=v1.hypothesis_id,
        evidence_ids=v1.evidence_ids,
        claim=DiscoveryClaim(statement="Direct", scope="Global"),
        epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
        scope="Global",
        validity_basis=v1,
    )
    d_ancestor = Discovery(
        discovery_id=uuid4(),
        hypothesis_id=v2.hypothesis_id,
        evidence_ids=v2.evidence_ids,
        claim=DiscoveryClaim(statement="Ancestor", scope="Global"),
        epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
        scope="Global",
        validity_basis=v2,
    )
    d_unrelated = Discovery(
        discovery_id=uuid4(),
        hypothesis_id=v3.hypothesis_id,
        evidence_ids=v3.evidence_ids,
        claim=DiscoveryClaim(statement="Unrelated semantic semantic", scope="Global"),
        epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
        scope="Global",
        validity_basis=v3,
    )

    ancestor_task.motivated_by_discovery_ids = [d_ancestor.discovery_id]
    parent_task.motivated_by_discovery_ids = [d_direct.discovery_id]

    from repositories.discovery_repository import DiscoveryRepository
    from repositories.task_repository import TaskRepository

    DiscoveryRepository(db_session).create(d_direct)
    DiscoveryRepository(db_session).create(d_ancestor)
    DiscoveryRepository(db_session).create(d_unrelated)
    TaskRepository(db_session).create(ancestor_task)
    TaskRepository(db_session).create(parent_task)

    engine = DiscoveryRetrievalEngine(db_session)
    request = RetrievalRequest(
        objective_id=uuid4(),
        parent_task_id=parent_task.task_id,
        query_text="semantic",
    )

    result = engine.retrieve(request, None)

    # direct (10) > ancestor (5) > unrelated semantic (0.x)
    assert len(result.motivation_candidates) == 3
    assert result.motivation_candidates[0].discovery_id == d_direct.discovery_id
    assert result.motivation_candidates[1].discovery_id == d_ancestor.discovery_id
    assert result.motivation_candidates[2].discovery_id == d_unrelated.discovery_id

    assert "direct_motivation" in result.motivation_candidates[0].structural_relations_used
    assert "ancestor_motivation" in result.motivation_candidates[1].structural_relations_used


def test_retrieval_excludes_invalid_lifecycle_states(db_session: Session, create_validity) -> None:
    v1 = create_validity()
    v2 = create_validity()
    v3 = create_validity()

    d_active = Discovery(
        discovery_id=uuid4(),
        hypothesis_id=v1.hypothesis_id,
        evidence_ids=v1.evidence_ids,
        claim=DiscoveryClaim(statement="Active", scope="Global"),
        epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
        scope="Global",
        validity_basis=v1,
    )
    d_invalidated = Discovery(
        discovery_id=uuid4(),
        hypothesis_id=v2.hypothesis_id,
        evidence_ids=v2.evidence_ids,
        claim=DiscoveryClaim(statement="Invalidated", scope="Global"),
        epistemic_status=DiscoveryEpistemicStatus.CONTRADICTED,
        scope="Global",
        validity_basis=v2,
        lifecycle_state=DiscoveryLifecycleState.INVALIDATED,
    )
    d_flagged = Discovery(
        discovery_id=uuid4(),
        hypothesis_id=v3.hypothesis_id,
        evidence_ids=v3.evidence_ids,
        claim=DiscoveryClaim(statement="Flagged", scope="Global"),
        epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
        scope="Global",
        validity_basis=v3,
        lifecycle_state=DiscoveryLifecycleState.FLAGGED,
        review_reasons=["Needs review"],
    )

    from repositories.discovery_repository import DiscoveryRepository

    DiscoveryRepository(db_session).create(d_active)
    DiscoveryRepository(db_session).create(d_invalidated)
    DiscoveryRepository(db_session).create(d_flagged)

    engine = DiscoveryRetrievalEngine(db_session)
    request = RetrievalRequest(
        objective_id=uuid4(),
        query_text="Active Invalidated Flagged",
    )

    result = engine.retrieve(request, None)

    ids = {c.discovery_id for c in result.motivation_candidates}
    other_ids = {c.discovery_id for c in result.other_relevant_discoveries}

    assert d_active.discovery_id in ids
    assert d_invalidated.discovery_id not in ids
    assert d_invalidated.discovery_id not in other_ids

    # Flagged is not eligible for motivation unless pinned
    assert d_flagged.discovery_id not in ids
    assert d_flagged.discovery_id in other_ids

    flagged_res = [
        c for c in result.other_relevant_discoveries if c.discovery_id == d_flagged.discovery_id
    ][0]
    assert "Flagged for review: Needs review" in flagged_res.flags


def test_retrieval_respects_session_frame_pins_and_exclusions(
    db_session: Session, create_validity
) -> None:
    v1 = create_validity()
    v2 = create_validity()

    d_pinned = Discovery(
        discovery_id=uuid4(),
        hypothesis_id=v1.hypothesis_id,
        evidence_ids=v1.evidence_ids,
        claim=DiscoveryClaim(statement="Pinned", scope="Global"),
        epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
        scope="Global",
        validity_basis=v1,
    )
    d_excluded = Discovery(
        discovery_id=uuid4(),
        hypothesis_id=v2.hypothesis_id,
        evidence_ids=v2.evidence_ids,
        claim=DiscoveryClaim(statement="Excluded", scope="Global"),
        epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
        scope="Global",
        validity_basis=v2,
    )

    from repositories.discovery_repository import DiscoveryRepository

    DiscoveryRepository(db_session).create(d_pinned)
    DiscoveryRepository(db_session).create(d_excluded)

    frame = SessionFrame(
        frame_topic="Test Frame",
        objective_snapshot="Snapshot",
        user_pins=[str(d_pinned.discovery_id), "task:not-a-discovery"],
        user_exclusions=[str(d_excluded.discovery_id)],
    )

    engine = DiscoveryRetrievalEngine(db_session)
    request = RetrievalRequest(
        objective_id=uuid4(),
        query_text="Pinned Excluded",
    )

    result = engine.retrieve(request, frame)

    ids = {c.discovery_id for c in result.motivation_candidates}
    assert d_pinned.discovery_id in ids
    assert d_excluded.discovery_id not in ids

    pinned_res = [
        c for c in result.motivation_candidates if c.discovery_id == d_pinned.discovery_id
    ][0]
    assert pinned_res.is_pinned is True
    assert result.exclusion_notes == [
        "Ignoring non-Discovery SessionFrame pin: 'task:not-a-discovery'."
    ]


def test_lexical_scorer() -> None:
    scorer = LexicalScorer()

    assert scorer.score("", "hello world") == 0.0
    assert scorer.score("world", "hello world") == 0.5
    assert scorer.score("test claim", "another test claim here") > 0.0
    assert scorer.score("totally unrelated", "different words here") == 0.0
