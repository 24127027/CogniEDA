"""M1-A SessionFrame lineage and ordering invariants."""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from cognieda.schemas import (
    Assumption,
    DataProfile,
    Discovery,
    DiscoveryClaim,
    DiscoveryEpistemicStatus,
    Evidence,
    EvidenceProvenance,
    Objective,
    SessionFrame,
    Task,
    TaskKind,
    TaskStatus,
    ValidityBasis,
)


def _profile() -> DataProfile:
    return DataProfile(row_count=0, column_count=0, columns=())


def _task(
    instruction: str,
    *,
    status: TaskStatus = TaskStatus.PENDING,
    objective_id: UUID | None = None,
) -> Task:
    return Task(
        objective_id=objective_id or uuid4(),
        kind=TaskKind.DATA,
        instruction=instruction,
        status=status,
    )


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


def _discovery() -> Discovery:
    hypothesis_id = uuid4()
    evidence_id = uuid4()
    return Discovery(
        hypothesis_id=hypothesis_id,
        evidence_ids=[evidence_id],
        claim=DiscoveryClaim(statement="A governed claim.", scope="scope:v1"),
        epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
        scope="scope:v1",
        validity_basis=ValidityBasis(
            data_profile_id=uuid4(),
            analysis_frame_refs=["analysis:v1"],
            hypothesis_id=hypothesis_id,
            evidence_ids=[evidence_id],
            method="governed method",
            decision_rule="Apply the governed rule.",
        ),
    )


def test_session_frame_retains_typed_state_in_insertion_order() -> None:
    objective = Objective(text="Understand retention")
    assumptions = [Assumption(text="First"), Assumption(text="Second")]
    tasks = [
        _task("First task", status=TaskStatus.COMPLETED, objective_id=objective.objective_id),
        _task("Second task", status=TaskStatus.COMPLETED, objective_id=objective.objective_id),
    ]
    profile = _profile()
    evidences = [_evidence(tasks[0], profile), _evidence(tasks[1], profile)]
    discoveries = [_discovery(), _discovery()]

    frame = SessionFrame(
        objective=objective,
        assumptions=assumptions,
        tasks=tasks,
        evidences=evidences,
        discoveries=discoveries,
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
    assert frame.discoveries == tuple(discoveries)


@pytest.mark.parametrize(
    ("field", "value_factory", "message"),
    [
        ("assumptions", lambda item: [item, item], "Assumption"),
        ("tasks", lambda item: [item, item], "Task"),
        ("evidences", lambda item: [item, item], "Evidence"),
        ("discoveries", lambda item: [item, item], "Discovery"),
    ],
)
def test_session_frame_rejects_duplicate_ids(field, value_factory, message) -> None:
    profile = _profile()
    task = _task("Profile data")
    values = {
        "assumptions": [],
        "tasks": [task],
        "evidences": [],
        "discoveries": [],
        "data_profile": profile,
    }
    item = {
        "assumptions": Assumption(text="Duplicate"),
        "tasks": task,
        "evidences": _evidence(task, profile),
        "discoveries": _discovery(),
    }[field]
    values[field] = value_factory(item)

    with pytest.raises(ValidationError, match=message):
        SessionFrame(**values)


def test_session_frame_rejects_orphan_evidence() -> None:
    profile = _profile()
    evidence = _evidence(_task("Missing task"), profile)

    with pytest.raises(ValidationError, match="orphan Evidence"):
        SessionFrame(data_profile=profile, evidences=[evidence])


def test_session_frame_rejects_evidence_without_data_profile() -> None:
    task = _task("Count rows", status=TaskStatus.COMPLETED)
    evidence = _evidence(task, _profile())

    with pytest.raises(ValidationError, match="without a DataProfile"):
        SessionFrame(tasks=[task], evidences=[evidence])


def test_session_frame_rejects_evidence_for_non_active_data_profile() -> None:
    task = _task("Count rows", status=TaskStatus.COMPLETED)
    evidence = _evidence(task, _profile())

    with pytest.raises(ValidationError, match="active SessionFrame DataProfile"):
        SessionFrame(tasks=[task], evidences=[evidence], data_profile=_profile())


def test_mutation_seams_preserve_invariants_and_order() -> None:
    frame = SessionFrame()
    profile = _profile()
    objective = Objective(text="Explore")
    first_task = _task("First", objective_id=objective.objective_id)
    second_task = _task(
        "Second",
        status=TaskStatus.COMPLETED,
        objective_id=objective.objective_id,
    )

    frame = frame.set_objective(objective)
    frame = frame.add_assumption(Assumption(text="Planning premise"))
    frame = frame.add_task(first_task)
    frame = frame.add_task(second_task)
    frame = frame.set_data_profile(profile)
    frame = frame.add_evidence(_evidence(second_task, profile))
    frame = frame.set_task_status(first_task.task_id, TaskStatus.RUNNING)

    assert [task.instruction for task in frame.tasks] == ["First", "Second"]
    assert frame.tasks[0] is not first_task
    assert frame.tasks[0].task_id == first_task.task_id
    assert frame.tasks[0].objective_id == first_task.objective_id
    assert frame.tasks[0].kind is first_task.kind
    assert frame.tasks[0].instruction == first_task.instruction
    assert frame.tasks[0].status is TaskStatus.RUNNING

    with pytest.raises(ValueError, match="orphan Evidence"):
        frame.add_evidence(_evidence(_task("Orphan"), profile))
    with pytest.raises(ValueError, match="DataProfile"):
        frame.set_data_profile(_profile())


def test_add_discovery_returns_successor_and_all_mutation_seams_preserve_it() -> None:
    discovery = _discovery()
    objective = Objective(text="Preserve retained Discovery.")
    task = _task(
        "Prepare work",
        status=TaskStatus.COMPLETED,
        objective_id=objective.objective_id,
    )
    profile = _profile()
    original = SessionFrame(
        objective=objective,
        tasks=(task,),
        data_profile=profile,
    ).add_discovery(discovery)

    successors = (
        original.set_objective(Objective(text="Refined Objective.")),
        original.add_assumption(Assumption(text="Planning-only premise")),
        original.add_task(_task("Second work", objective_id=objective.objective_id)),
        original.set_task_status(task.task_id, TaskStatus.COMPLETED),
        original.add_evidence(_evidence(task, profile)),
        original.set_data_profile(profile),
    )

    assert original.discoveries == (discovery,)
    assert all(frame.discoveries == (discovery,) for frame in successors)
    assert original.add_discovery(_discovery()).discoveries[0] is discovery


@pytest.mark.parametrize(
    "status",
    [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.FAILED],
)
def test_incomplete_task_cannot_admit_evidence(status: TaskStatus) -> None:
    task = _task("Run bounded analysis", status=status)
    profile = _profile()
    frame = SessionFrame(tasks=(task,), data_profile=profile)

    with pytest.raises(ValidationError, match="only for COMPLETED Tasks"):
        frame.add_evidence(_evidence(task, profile))

    assert frame.evidences == ()
    assert frame.tasks[0].status is status


def test_completed_task_can_admit_evidence() -> None:
    task = _task("Run bounded analysis", status=TaskStatus.COMPLETED)
    profile = _profile()
    evidence = _evidence(task, profile)
    frame = SessionFrame(tasks=(task,), data_profile=profile)

    frame = frame.add_evidence(evidence)

    assert frame.evidences == (evidence,)


def test_task_with_evidence_cannot_transition_away_from_completed() -> None:
    task = _task("Run bounded analysis", status=TaskStatus.COMPLETED)
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
    task = _task("Profile data")
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
