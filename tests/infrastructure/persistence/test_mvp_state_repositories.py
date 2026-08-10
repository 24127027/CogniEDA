"""Bounded SQLite coherence for active M1-A research-state schemas."""

from uuid import uuid4

import pytest

from cognieda.infrastructure.persistence.repositories import (
    AssumptionRepository,
    AssumptionUpdate,
    DataProfileRepository,
    EvidenceRepository,
    ObjectiveRepository,
    ObjectiveUpdate,
    SessionFrameRepository,
    TaskRepository,
    TaskUpdate,
)
from cognieda.schemas import (
    Assumption,
    DataProfile,
    Evidence,
    EvidenceProvenance,
    Objective,
    SessionFrame,
    Task,
    TaskStatus,
)


def test_minimum_objective_assumption_and_task_round_trip(db_session) -> None:
    objective = ObjectiveRepository(db_session).create(Objective(text="Understand retention"))
    assumption = AssumptionRepository(db_session).create(
        Assumption(text="Premium membership may guide planning")
    )
    task = TaskRepository(db_session).create(Task(instruction="Count retained customers"))

    assert ObjectiveRepository(db_session).get_by_id(objective.objective_id) == objective
    assert AssumptionRepository(db_session).get_by_id(assumption.assumption_id) == assumption
    assert TaskRepository(db_session).get_by_id(task.task_id) == task

    updated = TaskRepository(db_session).update(task.task_id, TaskUpdate(status=TaskStatus.RUNNING))
    assert updated is not None
    assert updated.status is TaskStatus.RUNNING
    assert updated.instruction == task.instruction


def test_objective_and_assumption_behavioral_updates_are_explicitly_deferred(db_session) -> None:
    with pytest.raises(NotImplementedError, match="M1-B"):
        ObjectiveRepository(db_session).update(uuid4(), ObjectiveUpdate(text="Changed"))
    with pytest.raises(NotImplementedError, match="M1-B"):
        AssumptionRepository(db_session).update(uuid4(), AssumptionUpdate(text="Changed"))


def test_data_profile_evidence_and_session_frame_round_trip_with_direct_lineage(db_session) -> None:
    task = TaskRepository(db_session).create(Task(instruction="Count rows"))
    task = TaskRepository(db_session).update(
        task.task_id,
        TaskUpdate(status=TaskStatus.COMPLETED),
    )
    assert task is not None
    profile = DataProfileRepository(db_session).create(
        DataProfile(row_count=3, column_count=0, columns=())
    )
    evidence = Evidence(
        task_id=task.task_id,
        data_profile_id=profile.data_profile_id,
        content={"row_count": 3, "columns": []},
        provenance=EvidenceProvenance(
            producer_role="data_explorer",
            work_reference=f"de:{task.task_id}",
            dataset_reference="dataset:customers.csv",
            data_profile_id=profile.data_profile_id,
            tool_reference="pandas:len",
        ),
    )

    persisted = EvidenceRepository(db_session).create(evidence)
    frame = SessionFrame(
        task_ids=(task.task_id,),
        data_profile_ids=(profile.data_profile_id,),
        active_data_profile_id=profile.data_profile_id,
        evidence_ids=(persisted.evidence_id,),
    )
    persisted_frame = SessionFrameRepository(db_session).create(frame)

    assert DataProfileRepository(db_session).get_by_id(profile.data_profile_id) == profile
    assert EvidenceRepository(db_session).get_by_id(evidence.evidence_id) == evidence
    assert persisted.content == {"row_count": 3, "columns": []}
    assert persisted.task_id == task.task_id
    assert persisted.data_profile_id == profile.data_profile_id
    assert persisted_frame == frame
    assert SessionFrameRepository(db_session).get_latest() == frame


def test_evidence_repository_rejects_missing_task_or_profile(db_session) -> None:
    profile = DataProfileRepository(db_session).create(
        DataProfile(row_count=0, column_count=0, columns=())
    )
    missing_task_evidence = Evidence(
        task_id=uuid4(),
        data_profile_id=profile.data_profile_id,
        content={"row_count": 0},
        provenance=EvidenceProvenance(
            producer_role="data_explorer",
            work_reference="de:missing-task",
            dataset_reference="dataset:empty.csv",
            data_profile_id=profile.data_profile_id,
        ),
    )
    with pytest.raises(ValueError, match="existing Task"):
        EvidenceRepository(db_session).create(missing_task_evidence)

    task = TaskRepository(db_session).create(Task(instruction="Count rows"))
    task = TaskRepository(db_session).update(
        task.task_id,
        TaskUpdate(status=TaskStatus.COMPLETED),
    )
    assert task is not None
    missing_profile_id = uuid4()
    missing_profile_evidence = Evidence(
        task_id=task.task_id,
        data_profile_id=missing_profile_id,
        content={"row_count": 0},
        provenance=EvidenceProvenance(
            producer_role="data_explorer",
            work_reference="de:missing-profile",
            dataset_reference="dataset:empty.csv",
            data_profile_id=missing_profile_id,
        ),
    )
    with pytest.raises(ValueError, match="existing DataProfile"):
        EvidenceRepository(db_session).create(missing_profile_evidence)


@pytest.mark.parametrize(
    "status",
    [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.FAILED],
)
def test_evidence_repository_rejects_incomplete_task(db_session, status: TaskStatus) -> None:
    task = TaskRepository(db_session).create(Task(instruction="Count rows", status=status))
    profile = DataProfileRepository(db_session).create(
        DataProfile(row_count=0, column_count=0, columns=())
    )
    evidence = Evidence(
        task_id=task.task_id,
        data_profile_id=profile.data_profile_id,
        content={"row_count": 0},
        provenance=EvidenceProvenance(
            producer_role="data_explorer",
            work_reference=f"de:{task.task_id}",
            dataset_reference="dataset:empty.csv",
            data_profile_id=profile.data_profile_id,
        ),
    )

    with pytest.raises(ValueError, match="COMPLETED Task"):
        EvidenceRepository(db_session).create(evidence)


def test_evidence_repository_accepts_completed_task(db_session) -> None:
    task = TaskRepository(db_session).create(
        Task(instruction="Count rows", status=TaskStatus.COMPLETED)
    )
    profile = DataProfileRepository(db_session).create(
        DataProfile(row_count=0, column_count=0, columns=())
    )
    evidence = Evidence(
        task_id=task.task_id,
        data_profile_id=profile.data_profile_id,
        content={"row_count": 0},
        provenance=EvidenceProvenance(
            producer_role="data_explorer",
            work_reference=f"de:{task.task_id}",
            dataset_reference="dataset:empty.csv",
            data_profile_id=profile.data_profile_id,
        ),
    )

    assert EvidenceRepository(db_session).create(evidence) == evidence
