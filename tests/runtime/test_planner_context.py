from __future__ import annotations

import pytest
from pydantic import ValidationError

from cognieda.agents.planner.types import PlannerOutput
from cognieda.execution import Capability
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
from cognieda.schemas.plan_revision import PlanRevision, PlanTaskBinding


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


def test_application_boundary_does_not_apply_transient_canonical_plan_objects() -> None:
    objective = Objective(text="Understand missingness.")
    task = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="Summarize missingness by column.",
    )
    revision = PlanRevision.create(
        objective_id=objective.objective_id,
        task_bindings=(
            PlanTaskBinding(
                task_id=task.task_id,
                required_capability=Capability.DATA_ANALYSIS,
                order_rank=0,
            ),
        ),
        authoritative_tasks=(task,),
    )
    current = SessionFrame()

    successor = apply_planner_output(
        current,
        PlannerOutput(
            response="Approval required.",
            proposed_objective=objective,
            proposed_tasks=(task,),
            proposed_plan_revision=revision,
        ),
    )

    assert successor is current
    assert successor.objective is None
    assert successor.tasks == ()
