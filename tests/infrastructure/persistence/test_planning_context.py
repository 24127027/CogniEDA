from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from cognieda.application.services import (
    PlannerContextPreparer,
    PlanningContextResolutionError,
    select_planner_context,
)
from cognieda.infrastructure.persistence import SqlitePlannerResearchState
from cognieda.infrastructure.persistence.repositories import (
    AssumptionRepository,
    DataProfileRepository,
    EvidenceRepository,
    ObjectiveRepository,
    SessionFrameRepository,
    TaskRepository,
    TaskUpdate,
)
from cognieda.schemas.artifacts import (
    Assumption,
    DataProfile,
    Evidence,
    Objective,
    SessionFrame,
    Task,
)
from cognieda.schemas.common import EvidenceProvenance
from cognieda.schemas.enums import TaskStatus


def _evidence(db_session, *, task: Task, profile: DataProfile, row_count: int) -> Evidence:
    return EvidenceRepository(db_session).create(
        Evidence(
            task_id=task.task_id,
            data_profile_id=profile.data_profile_id,
            content={"row_count": row_count},
            provenance=EvidenceProvenance(
                producer_role="data_explorer",
                work_reference=f"work:{task.task_id}",
                dataset_reference=f"dataset:{profile.data_profile_id}",
                data_profile_id=profile.data_profile_id,
            ),
        )
    )


def _admitted_state(db_session):
    objective = ObjectiveRepository(db_session).create(Objective(text="Understand size."))
    assumption = AssumptionRepository(db_session).create(
        Assumption(text="Rows represent customers.")
    )
    task = TaskRepository(db_session).create(
        Task(instruction="Count rows.", status=TaskStatus.COMPLETED)
    )
    profile = DataProfileRepository(db_session).create(
        DataProfile(row_count=42, column_count=0, columns=())
    )
    evidence = _evidence(db_session, task=task, profile=profile, row_count=42)
    frame = SessionFrame(
        objective_ids=(objective.objective_id,),
        active_objective_id=objective.objective_id,
        assumption_ids=(assumption.assumption_id,),
        task_ids=(task.task_id,),
        data_profile_ids=(profile.data_profile_id,),
        active_data_profile_id=profile.data_profile_id,
        evidence_ids=(evidence.evidence_id,),
    )
    return frame, objective, assumption, task, profile, evidence


def _build(db_session, frame: SessionFrame, request: str = "How many rows?"):
    selection = select_planner_context(frame)
    return PlannerContextPreparer(SqlitePlannerResearchState(db_session)).build(
        latest_request=request, selection=selection
    )


def test_selection_precedes_authoritative_materialization(db_session) -> None:
    frame, objective, assumption, task, profile, evidence = _admitted_state(db_session)
    selection = select_planner_context(frame)

    context = PlannerContextPreparer(SqlitePlannerResearchState(db_session)).build(
        latest_request="How many rows?", selection=selection
    )

    assert selection.objective_id == frame.active_objective_id
    assert set(type(selection).model_fields) == {
        "objective_id",
        "assumption_ids",
        "task_ids",
        "active_data_profile_id",
        "evidence_candidate_ids",
    }
    assert context.objective == objective
    assert context.assumptions == (assumption,)
    assert context.tasks == (task,)
    assert context.data_profile == profile
    assert context.evidences == (evidence,)
    assert "planning_context" not in frame.model_dump(mode="json")


def test_selector_bounds_historical_references_before_build(db_session) -> None:
    repository = TaskRepository(db_session)
    tasks = tuple(repository.create(Task(instruction=f"Task {index}")) for index in range(21))
    frame = SessionFrame(task_ids=tuple(task.task_id for task in tasks))
    selection = select_planner_context(frame, recent_reference_limit=20)

    context = PlannerContextPreparer(SqlitePlannerResearchState(db_session)).build(
        latest_request="Summarize current work", selection=selection
    )

    assert selection.task_ids == tuple(task.task_id for task in tasks[1:])
    assert tuple(task.task_id for task in context.tasks) == selection.task_ids
    assert tasks[0].task_id not in {task.task_id for task in context.tasks}


def test_later_context_observes_task_status_change_without_frame_replacement(db_session) -> None:
    task = TaskRepository(db_session).create(Task(instruction="Profile data."))
    frame = SessionFrame(task_ids=(task.task_id,))

    before = _build(db_session, frame, "Before")
    updated = TaskRepository(db_session).update(task.task_id, TaskUpdate(status=TaskStatus.RUNNING))
    after = _build(db_session, frame, "After")

    assert updated is not None
    assert before.tasks[0].status is TaskStatus.PENDING
    assert after.tasks[0].status is TaskStatus.RUNNING
    assert frame.task_ids == (task.task_id,)


@pytest.mark.parametrize(
    "frame",
    [
        (lambda object_id: SessionFrame(
            objective_ids=(object_id,), active_objective_id=object_id
        ))(uuid4()),
        SessionFrame(assumption_ids=(uuid4(),)),
        SessionFrame(task_ids=(uuid4(),)),
        (lambda object_id: SessionFrame(
            data_profile_ids=(object_id,), active_data_profile_id=object_id
        ))(uuid4()),
        SessionFrame(evidence_ids=(uuid4(),)),
    ],
)
def test_missing_selected_references_fail_closed(db_session, frame: SessionFrame) -> None:
    with pytest.raises(PlanningContextResolutionError, match="missing"):
        _build(db_session, frame, "Resolve state")


def test_design_b_evidence_expands_task_and_profile_dependencies_without_mutating_frame(
    db_session,
) -> None:
    task = TaskRepository(db_session).create(
        Task(instruction="Count rows.", status=TaskStatus.COMPLETED)
    )
    profile = DataProfileRepository(db_session).create(
        DataProfile(row_count=42, column_count=0, columns=())
    )
    evidence = _evidence(db_session, task=task, profile=profile, row_count=42)
    frame = SessionFrame(evidence_ids=(evidence.evidence_id,))

    context = _build(db_session, frame, "Use the admitted count")

    assert context.evidences == (evidence,)
    assert context.tasks == (task,)
    assert context.data_profile == profile
    assert frame.task_ids == ()
    assert frame.data_profile_ids == ()


class MissingEvidenceTaskState(SqlitePlannerResearchState):
    def __init__(self, db_session, *, missing_task_id: UUID) -> None:
        super().__init__(db_session)
        self._missing_task_id = missing_task_id

    def get_task(self, task_id: UUID) -> Task | None:
        if task_id == self._missing_task_id:
            return None
        return super().get_task(task_id)


def test_missing_required_evidence_dependency_fails_closed(db_session) -> None:
    task = TaskRepository(db_session).create(
        Task(instruction="Count rows.", status=TaskStatus.COMPLETED)
    )
    profile = DataProfileRepository(db_session).create(
        DataProfile(row_count=42, column_count=0, columns=())
    )
    evidence = _evidence(db_session, task=task, profile=profile, row_count=42)
    frame = SessionFrame(evidence_ids=(evidence.evidence_id,))
    selection = select_planner_context(frame)

    with pytest.raises(PlanningContextResolutionError, match="Task dependency"):
        PlannerContextPreparer(
            MissingEvidenceTaskState(db_session, missing_task_id=task.task_id)
        ).build(latest_request="Use evidence", selection=selection)


def test_invalid_authoritative_evidence_task_status_fails_closed(db_session) -> None:
    frame, _, _, task, _, _ = _admitted_state(db_session)
    TaskRepository(db_session).update(task.task_id, TaskUpdate(status=TaskStatus.FAILED))

    with pytest.raises(PlanningContextResolutionError, match="COMPLETED"):
        _build(db_session, frame, "Use evidence")


def test_historical_evidence_across_profiles_is_filtered_by_active_profile(db_session) -> None:
    task_one = TaskRepository(db_session).create(
        Task(instruction="Count v1.", status=TaskStatus.COMPLETED)
    )
    task_two = TaskRepository(db_session).create(
        Task(instruction="Count v2.", status=TaskStatus.COMPLETED)
    )
    profile_one = DataProfileRepository(db_session).create(
        DataProfile(row_count=10, column_count=0, columns=())
    )
    profile_two = DataProfileRepository(db_session).create(
        DataProfile(row_count=20, column_count=0, columns=())
    )
    evidence_one = _evidence(db_session, task=task_one, profile=profile_one, row_count=10)
    evidence_two = _evidence(db_session, task=task_two, profile=profile_two, row_count=20)
    frame = SessionFrame(
        data_profile_ids=(profile_one.data_profile_id, profile_two.data_profile_id),
        active_data_profile_id=profile_two.data_profile_id,
        evidence_ids=(evidence_one.evidence_id, evidence_two.evidence_id),
    )
    TaskRepository(db_session).update(
        task_one.task_id, TaskUpdate(status=TaskStatus.FAILED)
    )

    context = _build(db_session, frame, "Use the active dataset")

    assert context.data_profile == profile_two
    assert context.evidences == (evidence_two,)
    assert context.tasks == (task_two,)
    assert frame.evidence_ids == (evidence_one.evidence_id, evidence_two.evidence_id)


def test_session_frame_persistence_round_trip_contains_cumulative_references(db_session) -> None:
    frame, *_ = _admitted_state(db_session)

    persisted = SessionFrameRepository(db_session).create(frame)
    payload = persisted.model_dump(mode="json")

    assert persisted == frame
    assert set(payload) == {
        "objective_ids",
        "active_objective_id",
        "assumption_ids",
        "task_ids",
        "data_profile_ids",
        "active_data_profile_id",
        "evidence_ids",
    }
