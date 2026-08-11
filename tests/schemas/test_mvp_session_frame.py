"""M1-A SessionFrame lineage and ordering invariants."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

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


def _profile() -> DataProfile:
    return DataProfile(row_count=0, column_count=0, columns=())


def _evidence(task: Task, profile: DataProfile) -> Evidence:
    return Evidence(
        task_id=task.task_id,
        data_profile_id=profile.data_profile_id,
        content={"row_count": 0},
        provenance=EvidenceProvenance(
            producer_role="data_explorer",
            work_reference=f"de:{task.task_id}",
            dataset_reference="dataset:empty.csv",
            data_profile_id=profile.data_profile_id,
            tool_reference="pandas:len",
        ),
    )


def test_session_frame_retains_typed_state_in_insertion_order() -> None:
    objective = Objective(text="Understand retention")
    assumptions = [Assumption(text="First"), Assumption(text="Second")]
    tasks = [
        Task(instruction="First task", status=TaskStatus.COMPLETED),
        Task(instruction="Second task", status=TaskStatus.COMPLETED),
    ]
    profile = _profile()
    evidences = [_evidence(tasks[0], profile), _evidence(tasks[1], profile)]

    frame = SessionFrame(
        objective=objective,
        assumptions=assumptions,
        tasks=tasks,
        evidences=evidences,
        data_profile=profile,
    )

    assert frame.objective is objective
    assert [item.text for item in frame.assumptions] == ["First", "Second"]
    assert [item.instruction for item in frame.tasks] == ["First task", "Second task"]
    assert [item.evidence_id for item in frame.evidences] == [
        evidences[0].evidence_id,
        evidences[1].evidence_id,
    ]
    assert frame.data_profile is profile


@pytest.mark.parametrize(
    ("field", "value_factory", "message"),
    [
        ("assumptions", lambda item: [item, item], "Assumption"),
        ("tasks", lambda item: [item, item], "Task"),
        ("evidences", lambda item: [item, item], "Evidence"),
    ],
)
def test_session_frame_rejects_duplicate_ids(field, value_factory, message) -> None:
    profile = _profile()
    task = Task(instruction="Profile data")
    values = {
        "assumptions": [],
        "tasks": [task],
        "evidences": [],
        "data_profile": profile,
    }
    item = {
        "assumptions": Assumption(text="Duplicate"),
        "tasks": task,
        "evidences": _evidence(task, profile),
    }[field]
    values[field] = value_factory(item)

    with pytest.raises(ValidationError, match=message):
        SessionFrame(**values)


def test_session_frame_rejects_orphan_evidence() -> None:
    profile = _profile()
    evidence = _evidence(Task(instruction="Missing task"), profile)

    with pytest.raises(ValidationError, match="orphan Evidence"):
        SessionFrame(data_profile=profile, evidences=[evidence])


def test_session_frame_rejects_evidence_without_data_profile() -> None:
    task = Task(instruction="Count rows", status=TaskStatus.COMPLETED)
    evidence = _evidence(task, _profile())

    with pytest.raises(ValidationError, match="without a DataProfile"):
        SessionFrame(tasks=[task], evidences=[evidence])


def test_session_frame_rejects_evidence_for_non_active_data_profile() -> None:
    task = Task(instruction="Count rows", status=TaskStatus.COMPLETED)
    evidence = _evidence(task, _profile())

    with pytest.raises(ValidationError, match="active SessionFrame DataProfile"):
        SessionFrame(tasks=[task], evidences=[evidence], data_profile=_profile())


def test_mutation_seams_preserve_invariants_and_order() -> None:
    frame = SessionFrame()
    profile = _profile()
    first_task = Task(instruction="First")
    second_task = Task(instruction="Second", status=TaskStatus.COMPLETED)

    frame = frame.set_objective(Objective(text="Explore"))
    frame = frame.add_assumption(Assumption(text="Planning premise"))
    frame = frame.add_task(first_task)
    frame = frame.add_task(second_task)
    frame = frame.set_data_profile(profile)
    frame = frame.add_evidence(_evidence(second_task, profile))
    frame = frame.set_task_status(first_task.task_id, TaskStatus.RUNNING)

    assert [task.instruction for task in frame.tasks] == ["First", "Second"]
    assert frame.tasks[0] is not first_task
    assert frame.tasks[0].task_id == first_task.task_id
    assert frame.tasks[0].instruction == first_task.instruction
    assert frame.tasks[0].status is TaskStatus.RUNNING

    with pytest.raises(ValueError, match="orphan Evidence"):
        frame.add_evidence(_evidence(Task(instruction="Orphan"), profile))
    with pytest.raises(ValueError, match="DataProfile"):
        frame.set_data_profile(_profile())


@pytest.mark.parametrize(
    "status",
    [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.FAILED],
)
def test_incomplete_task_cannot_admit_evidence(status: TaskStatus) -> None:
    task = Task(instruction="Run bounded analysis", status=status)
    profile = _profile()
    frame = SessionFrame(tasks=(task,), data_profile=profile)

    with pytest.raises(ValidationError, match="only for COMPLETED Tasks"):
        frame.add_evidence(_evidence(task, profile))

    assert frame.evidences == ()
    assert frame.tasks[0].status is status


def test_completed_task_can_admit_evidence() -> None:
    task = Task(instruction="Run bounded analysis", status=TaskStatus.COMPLETED)
    profile = _profile()
    evidence = _evidence(task, profile)
    frame = SessionFrame(tasks=(task,), data_profile=profile)

    frame = frame.add_evidence(evidence)

    assert frame.evidences == (evidence,)


def test_task_with_evidence_cannot_transition_away_from_completed() -> None:
    task = Task(instruction="Run bounded analysis", status=TaskStatus.COMPLETED)
    profile = _profile()
    frame = SessionFrame(
        tasks=(task,),
        evidences=(_evidence(task, profile),),
        data_profile=profile,
    )

    with pytest.raises(ValidationError, match="only for COMPLETED Tasks"):
        frame.set_task_status(task.task_id, TaskStatus.FAILED)

    assert frame.tasks[0].status is TaskStatus.COMPLETED


def test_session_frame_collections_cannot_bypass_validation_by_direct_mutation() -> None:
    task = Task(instruction="Profile data")
    frame = SessionFrame(tasks=(task,))

    with pytest.raises(AttributeError):
        frame.tasks.append(task)  # type: ignore[attr-defined]
    with pytest.raises(AttributeError):
        frame.evidences.append(_evidence(task, _profile()))  # type: ignore[attr-defined]
    with pytest.raises(ValidationError, match="frozen"):
        frame.tasks = (*frame.tasks, task)


def test_session_frame_rejects_unknown_task_status_update() -> None:
    with pytest.raises(ValueError, match="does not contain"):
        SessionFrame().set_task_status(uuid4(), TaskStatus.COMPLETED)


def test_empty_session_frame_projects_to_empty_membership() -> None:
    membership = SessionFrame().to_membership()

    assert all(value in ((), None) for value in membership.model_dump().values())


def test_materialized_objective_and_data_profile_project_to_membership_and_selectors() -> None:
    objective = Objective(text="Understand retention")
    profile = _profile()

    membership = SessionFrame(objective=objective, data_profile=profile).to_membership()

    assert membership.objective_ids == (objective.objective_id,)
    assert membership.active_objective_id == objective.objective_id
    assert membership.data_profile_ids == (profile.data_profile_id,)
    assert membership.active_data_profile_id == profile.data_profile_id


def test_materialized_collections_project_exact_ids_without_fabricated_membership() -> None:
    assumptions = (Assumption(text="First"), Assumption(text="Second"))
    tasks = (
        Task(instruction="First", status=TaskStatus.COMPLETED),
        Task(instruction="Second", status=TaskStatus.COMPLETED),
    )
    profile = _profile()
    evidences = (_evidence(tasks[0], profile), _evidence(tasks[1], profile))

    membership = SessionFrame(
        assumptions=assumptions,
        tasks=tasks,
        data_profile=profile,
        evidences=evidences,
    ).to_membership()

    assert membership.assumption_ids == tuple(item.assumption_id for item in assumptions)
    assert membership.task_ids == tuple(item.task_id for item in tasks)
    assert membership.evidence_ids == tuple(item.evidence_id for item in evidences)
    assert membership.hypothesis_ids == ()
    assert membership.discovery_ids == ()
