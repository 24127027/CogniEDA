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


def test_planner_context_exact_fields_and_no_singular_or_plan_fields() -> None:
    assert tuple(PlannerContext.model_fields) == (
        "objectives",
        "assumptions",
        "hypotheses",
        "evidences",
        "discoveries",
        "data_profile",
    )
    assert "active_plans" not in PlannerContext.model_fields
    assert "active_plan" not in PlannerContext.model_fields
    assert "objective" not in PlannerContext.model_fields


def test_builder_materializes_all_readable_frame_members() -> None:
    frame = _full_frame()

    context = build_planner_context(frame)

    assert context.objectives == frame.objectives
    assert len(context.objectives) == 2
    assert context.assumptions == frame.assumptions
    assert context.hypotheses == frame.hypotheses
    assert context.evidences == frame.evidences
    assert context.discoveries == frame.discoveries
    assert context.data_profile == frame.data_profile
    assert "active_plans" not in PlannerContext.model_fields
    assert "active_plan" not in PlannerContext.model_fields
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


def test_builder_does_not_accept_plan_parameters() -> None:
    frame = _full_frame()
    with pytest.raises(TypeError):
        build_planner_context(frame, active_plans=())  # type: ignore[call-arg]
