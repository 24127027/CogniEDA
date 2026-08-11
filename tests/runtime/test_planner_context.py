from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from cognieda.agents.planner.types import PlannerOutput
from cognieda.runtime.conversation import ConversationHistory
from cognieda.runtime.planner_context import apply_planner_output, build_planning_context
from cognieda.schemas.artifacts import (
    Assumption,
    DataProfile,
    Evidence,
    Objective,
    SessionFrame,
    Task,
)
from cognieda.schemas.common import EvidenceProvenance
from cognieda.schemas.enums import TaskKind, TaskStatus


def _full_frame() -> SessionFrame:
    objective = Objective(text="Understand dataset completeness.")
    assumption = Assumption(text="Rows represent independent observations.")
    task = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="Count rows.",
        status=TaskStatus.COMPLETED,
    )
    profile = DataProfile(row_count=42, column_count=0, columns=())
    evidence = Evidence(
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
    return SessionFrame(
        objective=objective,
        assumptions=(assumption,),
        tasks=(task,),
        evidences=(evidence,),
        data_profile=profile,
    )


def test_builder_exactly_materializes_every_retained_session_frame_member() -> None:
    frame = _full_frame()
    history = ConversationHistory()

    context = build_planning_context(frame, history)

    assert context.objective == frame.objective
    assert context.assumptions == frame.assumptions
    assert context.tasks == frame.tasks
    assert context.evidences == frame.evidences
    assert context.data_profile == frame.data_profile
    assert context.conversation_history == history
    with pytest.raises(ValidationError, match="frozen"):
        context.tasks = ()


def test_application_boundary_applies_objective_and_assumption_results() -> None:
    original = Objective(text="Understand retention.")
    refined = Objective(text="Understand retention drivers.")
    assumption = Assumption(text="Rows represent customers.")
    current = SessionFrame(objective=original)

    successor = apply_planner_output(
        current,
        PlannerOutput(
            response="Updated planning state.",
            created_objective=refined,
            created_assumption=assumption,
        ),
    )

    assert current.objective == original
    assert current.assumptions == ()
    assert successor.objective == refined
    assert successor.assumptions == (assumption,)


def test_application_boundary_applies_terminal_task_with_exact_semantic_identity() -> None:
    objective = Objective(text="Understand missingness.")
    task = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="Summarize missingness by column.",
        status=TaskStatus.COMPLETED,
    )

    successor = apply_planner_output(
        SessionFrame(objective=objective),
        PlannerOutput(response="Work completed.", created_task=task),
    )

    applied = successor.tasks[0]
    assert applied.status is TaskStatus.COMPLETED
    assert (
        applied.task_id,
        applied.objective_id,
        applied.kind,
        applied.instruction,
    ) == (
        task.task_id,
        task.objective_id,
        task.kind,
        task.instruction,
    )


def test_application_boundary_rejects_task_for_another_objective() -> None:
    objective = Objective(text="Understand missingness.")
    mismatched_task = Task(
        objective_id=uuid4(),
        kind=TaskKind.DATA,
        instruction="Summarize missingness by column.",
        status=TaskStatus.FAILED,
    )

    with pytest.raises(ValueError, match="active Objective identity"):
        apply_planner_output(
            SessionFrame(objective=objective),
            PlannerOutput(response="Work failed.", created_task=mismatched_task),
        )
