from __future__ import annotations

import pytest
from pydantic import ValidationError

from cognieda.agents.planner.context import PlannerContext
from cognieda.runtime.planner_context import build_planner_context
from cognieda.schemas import (
    Assumption,
    DataProfile,
    Discovery,
    DiscoveryClaim,
    Evidence,
    EvidenceProvenance,
    Hypothesis,
    Objective,
    Plan,
    SessionFrame,
    Task,
    ValidityBasis,
)
from cognieda.schemas.enums import DiscoveryEpistemicStatus, TaskKind, TaskStatus


def _full_frame() -> SessionFrame:
    objective_1 = Objective(text="Understand dataset completeness.")
    objective_2 = Objective(text="Understand churn rate.")
    assumption = Assumption(text="Rows represent independent observations.")
    task = Task(
        objective_id=objective_1.objective_id,
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
    hypothesis = Hypothesis(
        task_id=task.task_id,
        profile_id=profile.data_profile_id,
        statement="The admitted dataset contains 42 rows.",
        scope="dataset:v1",
        validation_method="row count",
        evidence_expectation="one admitted row-count observation",
    )
    discovery = Discovery(
        hypothesis_id=hypothesis.hypothesis_id,
        evidence_ids=[evidence.evidence_id],
        claim=DiscoveryClaim(
            statement="The admitted dataset contains 42 rows.",
            scope="dataset:v1",
        ),
        epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
        scope="dataset:v1",
        validity_basis=ValidityBasis(
            data_profile_id=profile.data_profile_id,
            analysis_frame_refs=["analysis:row-count"],
            hypothesis_id=hypothesis.hypothesis_id,
            evidence_ids=[evidence.evidence_id],
            method="row count",
            decision_rule="Support when the admitted count is 42.",
        ),
    )
    return SessionFrame(
        objectives=(objective_1, objective_2),
        assumptions=(assumption,),
        hypotheses=(hypothesis,),
        evidences=(evidence,),
        discoveries=(discovery,),
        data_profile=profile,
    )


def test_planner_context_exact_fields_and_no_singular_fields() -> None:
    assert tuple(PlannerContext.model_fields) == (
        "active_plans",
        "objectives",
        "assumptions",
        "hypotheses",
        "evidences",
        "discoveries",
        "data_profile",
    )
    assert "active_plan" not in PlannerContext.model_fields
    assert "objective" not in PlannerContext.model_fields


def test_builder_materializes_all_readable_frame_members_and_zero_active_plans() -> None:
    frame = _full_frame()

    context = build_planner_context(frame)

    assert context.active_plans == ()
    assert context.objectives == frame.objectives
    assert len(context.objectives) == 2
    assert context.assumptions == frame.assumptions
    assert context.hypotheses == frame.hypotheses
    assert context.evidences == frame.evidences
    assert context.discoveries == frame.discoveries
    assert context.data_profile == frame.data_profile
    with pytest.raises(ValidationError, match="frozen"):
        context.hypotheses = ()


def test_session_frame_retains_discovery_membership_immutably() -> None:
    frame = _full_frame()
    discovery = frame.discoveries[0]
    empty = SessionFrame()

    successor = empty.add_discovery(discovery)

    assert empty.discoveries == ()
    assert successor.discoveries == (discovery,)
    with pytest.raises(ValidationError, match="duplicate Discovery"):
        SessionFrame(discoveries=(discovery, discovery))


def test_builder_materializes_exact_active_plans_for_frame_objectives() -> None:
    frame = _full_frame()
    assert len(frame.objectives) >= 2
    task_1 = Task(
        objective_id=frame.objectives[0].objective_id,
        kind=TaskKind.DATA,
        instruction="Count rows.",
    )
    plan_1 = Plan(
        objective=frame.objectives[0],
        assumptions=frame.assumptions,
        tasks=(task_1,),
    )
    task_2 = Task(
        objective_id=frame.objectives[1].objective_id,
        kind=TaskKind.DATA,
        instruction="Calculate churn.",
    )
    plan_2 = Plan(
        objective=frame.objectives[1],
        assumptions=(),
        tasks=(task_2,),
    )

    context = build_planner_context(
        frame,
        active_plans=(plan_1, plan_2),
    )

    assert context.active_plans == (plan_1, plan_2)
    assert context.objectives == frame.objectives


def test_builder_accepts_subset_of_objectives_with_active_plans() -> None:
    frame = _full_frame()
    task_1 = Task(
        objective_id=frame.objectives[0].objective_id,
        kind=TaskKind.DATA,
        instruction="Count rows.",
    )
    plan_1 = Plan(
        objective=frame.objectives[0],
        assumptions=frame.assumptions,
        tasks=(task_1,),
    )

    context = build_planner_context(frame, active_plans=(plan_1,))

    assert context.active_plans == (plan_1,)
    assert context.objectives == frame.objectives


def test_builder_rejects_active_plan_for_objective_outside_frame() -> None:
    frame = _full_frame()
    other = Objective(text="Outside Objective.")
    plan = Plan(objective=other, tasks=())

    with pytest.raises(
        ValueError,
        match="Active Plan focal Objective must belong to the SessionFrame",
    ):
        build_planner_context(
            frame,
            active_plans=(plan,),
        )


def test_builder_rejects_duplicate_active_plan_ids() -> None:
    frame = _full_frame()
    task = Task(
        objective_id=frame.objectives[0].objective_id,
        kind=TaskKind.DATA,
        instruction="Count rows.",
    )
    plan = Plan(
        objective=frame.objectives[0],
        tasks=(task,),
    )

    with pytest.raises(ValueError, match="duplicate active Plan IDs"):
        build_planner_context(frame, active_plans=(plan, plan))


def test_builder_rejects_multiple_active_plans_for_same_objective() -> None:
    frame = _full_frame()
    task_1 = Task(
        objective_id=frame.objectives[0].objective_id,
        kind=TaskKind.DATA,
        instruction="Task 1.",
    )
    task_2 = Task(
        objective_id=frame.objectives[0].objective_id,
        kind=TaskKind.DATA,
        instruction="Task 2.",
    )
    plan_1 = Plan(objective=frame.objectives[0], tasks=(task_1,))
    plan_2 = Plan(objective=frame.objectives[0], tasks=(task_2,))

    with pytest.raises(ValueError, match="multiple active Plans for the same Objective"):
        build_planner_context(frame, active_plans=(plan_1, plan_2))
