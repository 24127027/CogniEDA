from __future__ import annotations

from uuid import uuid4

import pytest

from cognieda.agents.planner.context import (
    BuildPlanningContext,
    PlanningContextResolutionError,
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
    evidence = EvidenceRepository(db_session).create(
        Evidence(
            task_id=task.task_id,
            data_profile_id=profile.data_profile_id,
            content={"row_count": 42},
            provenance=EvidenceProvenance(
                producer_role="data_explorer",
                work_reference="work:count-rows",
                dataset_reference="dataset:v1",
                data_profile_id=profile.data_profile_id,
            ),
        )
    )
    frame = SessionFrame(
        objective_id=objective.objective_id,
        assumption_ids=(assumption.assumption_id,),
        task_ids=(task.task_id,),
        evidence_ids=(evidence.evidence_id,),
        data_profile_id=profile.data_profile_id,
    )
    return frame, objective, assumption, task, profile, evidence


def test_build_planning_context_resolves_current_authoritative_objects(db_session) -> None:
    frame, objective, assumption, task, profile, evidence = _admitted_state(db_session)
    builder = BuildPlanningContext(SqlitePlannerResearchState(db_session))

    context = builder.build(latest_request="How many rows?", frame=frame)

    assert context.latest_request == "How many rows?"
    assert context.objective == objective
    assert context.assumptions == (assumption,)
    assert context.tasks == (task,)
    assert context.data_profile == profile
    assert context.evidences == (evidence,)
    assert "planning_context" not in frame.model_dump(mode="json")


def test_later_context_observes_task_status_change_without_frame_replacement(db_session) -> None:
    task = TaskRepository(db_session).create(Task(instruction="Profile data."))
    frame = SessionFrame(task_ids=(task.task_id,))
    builder = BuildPlanningContext(SqlitePlannerResearchState(db_session))

    before = builder.build(latest_request="Before", frame=frame)
    updated = TaskRepository(db_session).update(task.task_id, TaskUpdate(status=TaskStatus.RUNNING))
    after = builder.build(latest_request="After", frame=frame)

    assert updated is not None
    assert before.tasks[0].status is TaskStatus.PENDING
    assert after.tasks[0].status is TaskStatus.RUNNING
    assert frame.task_ids == (task.task_id,)


@pytest.mark.parametrize(
    "frame",
    [
        SessionFrame(objective_id=uuid4()),
        SessionFrame(assumption_ids=(uuid4(),)),
        SessionFrame(task_ids=(uuid4(),)),
        SessionFrame(data_profile_id=uuid4()),
        SessionFrame(evidence_ids=(uuid4(),)),
    ],
)
def test_missing_session_frame_references_fail_closed(db_session, frame: SessionFrame) -> None:
    builder = BuildPlanningContext(SqlitePlannerResearchState(db_session))

    with pytest.raises(PlanningContextResolutionError, match="missing"):
        builder.build(latest_request="Resolve state", frame=frame)


def test_evidence_membership_without_required_task_and_profile_is_not_eligible(db_session) -> None:
    frame, _, _, _, _, evidence = _admitted_state(db_session)
    builder = BuildPlanningContext(SqlitePlannerResearchState(db_session))
    evidence_only = SessionFrame(evidence_ids=(evidence.evidence_id,))

    with pytest.raises(PlanningContextResolutionError, match="Task is not referenced"):
        builder.build(latest_request="Use evidence", frame=evidence_only)

    assert frame.evidence_ids == evidence_only.evidence_ids


def test_authoritative_task_status_and_profile_mismatch_invalidate_context(db_session) -> None:
    frame, _, _, task, _, _ = _admitted_state(db_session)
    other_profile = DataProfileRepository(db_session).create(
        DataProfile(row_count=1, column_count=0, columns=())
    )
    builder = BuildPlanningContext(SqlitePlannerResearchState(db_session))

    TaskRepository(db_session).update(task.task_id, TaskUpdate(status=TaskStatus.FAILED))
    with pytest.raises(PlanningContextResolutionError, match="COMPLETED"):
        builder.build(latest_request="Use evidence", frame=frame)

    TaskRepository(db_session).update(task.task_id, TaskUpdate(status=TaskStatus.COMPLETED))
    mismatched = frame.set_data_profile_id(other_profile.data_profile_id)
    with pytest.raises(PlanningContextResolutionError, match="match"):
        builder.build(latest_request="Use evidence", frame=mismatched)


def test_session_frame_persistence_round_trip_contains_references_not_objects(db_session) -> None:
    frame, *_ = _admitted_state(db_session)

    persisted = SessionFrameRepository(db_session).create(frame)
    payload = persisted.model_dump(mode="json")

    assert persisted == frame
    assert set(payload) == {
        "objective_id",
        "assumption_ids",
        "task_ids",
        "evidence_ids",
        "data_profile_id",
    }
