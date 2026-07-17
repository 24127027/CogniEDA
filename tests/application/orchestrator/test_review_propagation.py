from uuid import uuid4

from application.orchestrator.review_propagation import propagate_discovery_review
from db.models import DiscoveryRecord
from repositories.task_repository import TaskRepository
from schemas.artifacts import Task
from schemas.enums import DiscoveryLifecycleState, TaskLifecycleState


def test_propagate_discovery_review_flags_motivated_tasks(db_session):
    from sqlalchemy import text

    db_session.execute(text("PRAGMA foreign_keys=OFF"))
    db_session.commit()
    # Setup test discovery
    discovery_id = uuid4()
    db_session.add(
        DiscoveryRecord(
            discovery_id=discovery_id,
            claim_statement="Test claim",
            epistemic_status="supported",
            scope="test",
            hypothesis_id=uuid4(),
            evidence_ids=[],
            lifecycle_state=DiscoveryLifecycleState.FLAGGED,
            decision_rules=[],
        )
    )

    # Setup unflagged task motivated by this discovery
    task_repo = TaskRepository(db_session)
    t1 = task_repo.create(
        Task(
            title="T1",
            description="T1 description",
            lifecycle_state=TaskLifecycleState.ACTIVE,
            motivated_by_discovery_ids=[discovery_id],
        )
    )

    # Setup task NOT motivated by this discovery
    t2 = task_repo.create(
        Task(
            title="T2",
            description="T2 description",
            lifecycle_state=TaskLifecycleState.ACTIVE,
            motivated_by_discovery_ids=[],
        )
    )

    db_session.commit()

    # Run propagation
    propagate_discovery_review(db_session, discovery_id)

    # Assert T1 is flagged (reasons updated)
    updated_t1 = task_repo.get_by_id(t1.task_id)
    assert len(updated_t1.review_reasons) == 1
    assert "entered review state (flagged)" in updated_t1.review_reasons[0]

    # Assert T2 is NOT flagged
    updated_t2 = task_repo.get_by_id(t2.task_id)
    assert len(updated_t2.review_reasons) == 0
