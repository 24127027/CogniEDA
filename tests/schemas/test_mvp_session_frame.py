"""M1-A SessionFrame lineage and ordering invariants."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from schemas import (
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
    tasks = [Task(instruction="First task"), Task(instruction="Second task")]
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
    task = Task(instruction="Count rows")
    evidence = _evidence(task, _profile())

    with pytest.raises(ValidationError, match="without a DataProfile"):
        SessionFrame(tasks=[task], evidences=[evidence])


def test_session_frame_rejects_evidence_for_non_active_data_profile() -> None:
    task = Task(instruction="Count rows")
    evidence = _evidence(task, _profile())

    with pytest.raises(ValidationError, match="active SessionFrame DataProfile"):
        SessionFrame(tasks=[task], evidences=[evidence], data_profile=_profile())


def test_mutation_seams_preserve_invariants_and_order() -> None:
    frame = SessionFrame()
    profile = _profile()
    first_task = Task(instruction="First")
    second_task = Task(instruction="Second")

    frame.set_objective(Objective(text="Explore"))
    frame.add_assumption(Assumption(text="Planning premise"))
    frame.add_task(first_task)
    frame.add_task(second_task)
    frame.set_data_profile(profile)
    frame.add_evidence(_evidence(second_task, profile))
    frame.set_task_status(first_task.task_id, TaskStatus.RUNNING)

    assert [task.instruction for task in frame.tasks] == ["First", "Second"]
    assert frame.tasks[0].status is TaskStatus.RUNNING

    with pytest.raises(ValueError, match="orphan Evidence"):
        frame.add_evidence(_evidence(Task(instruction="Orphan"), profile))
    with pytest.raises(ValueError, match="DataProfile"):
        frame.set_data_profile(_profile())


def test_failed_task_creates_or_requires_no_evidence() -> None:
    task = Task(instruction="Run bounded analysis", status=TaskStatus.FAILED)
    frame = SessionFrame(tasks=[task], data_profile=_profile())

    assert frame.evidences == []
    assert frame.tasks[0].status is TaskStatus.FAILED


def test_session_frame_rejects_unknown_task_status_update() -> None:
    with pytest.raises(ValueError, match="does not contain"):
        SessionFrame().set_task_status(uuid4(), TaskStatus.COMPLETED)
