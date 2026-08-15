from __future__ import annotations

import pytest
from pydantic import ValidationError

from cognieda.agents.planner.context import PlannerContext
from cognieda.agents.planner.types import PlannerOutput, PlannerResult
from cognieda.schemas import (
    Assumption,
    DataProfile,
    Discovery,
    DiscoveryClaim,
    Evidence,
    EvidenceProvenance,
    Hypothesis,
    Objective,
    Task,
    ValidityBasis,
)
from cognieda.schemas.enums import DiscoveryEpistemicStatus, TaskKind
from cognieda.schemas.plan import Plan


def _task(objective: Objective, instruction: str = "Profile missing values.") -> Task:
    return Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction=instruction,
    )


def _plan(objective: Objective, tasks: tuple[Task, ...]) -> Plan:
    return Plan(
        objective=objective,
        tasks=tasks,
    )


def _evidence_and_discovery(
    task: Task,
    profile: DataProfile,
) -> tuple[Evidence, Hypothesis, Discovery]:
    evidence = Evidence(
        task_id=task.task_id,
        data_profile_id=profile.data_profile_id,
        content={"missing": 0},
        provenance=EvidenceProvenance(
            producer_role="data_explorer",
            work_reference="work:missingness",
            dataset_reference="dataset:v1",
            data_profile_id=profile.data_profile_id,
        ),
    )
    hypothesis = Hypothesis(
        task_id=task.task_id,
        profile_id=profile.data_profile_id,
        statement="The admitted dataset has no missing values.",
        scope="dataset:v1",
        validation_method="complete count",
        evidence_expectation="one admitted missingness observation",
    )
    discovery = Discovery(
        hypothesis_id=hypothesis.hypothesis_id,
        evidence_ids=[evidence.evidence_id],
        claim=DiscoveryClaim(
            statement="No values were missing in the admitted dataset.",
            scope="dataset:v1",
        ),
        epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
        scope="dataset:v1",
        validity_basis=ValidityBasis(
            data_profile_id=profile.data_profile_id,
            analysis_frame_refs=["analysis:missingness"],
            hypothesis_id=hypothesis.hypothesis_id,
            evidence_ids=[evidence.evidence_id],
            method="complete count",
            decision_rule="Support when missing count equals zero.",
        ),
    )
    return evidence, hypothesis, discovery


def test_planner_context_and_result_have_exact_canonical_fields() -> None:
    assert tuple(PlannerContext.model_fields) == (
        "active_plan",
        "objective",
        "assumptions",
        "hypotheses",
        "evidences",
        "discoveries",
        "data_profile",
    )
    assert tuple(PlannerResult.model_fields) == (
        "plan",
        "response",
        "human_input_request",
        "continue_execution",
        "discard_candidate",
    )
    assert tuple(PlannerOutput.model_fields) == ("result", "messages", "error")


def test_planner_context_retains_all_typed_readable_state() -> None:
    objective = Objective(text="Understand customer retention.")
    assumption = Assumption(text="Rows represent customers.")
    task = _task(objective)
    profile = DataProfile(row_count=10, column_count=0, columns=())
    evidence, hypothesis, discovery = _evidence_and_discovery(task, profile)
    active_plan = _plan(objective, (task,))

    context = PlannerContext(
        active_plan=active_plan,
        objective=objective,
        assumptions=(assumption,),
        hypotheses=(hypothesis,),
        evidences=(evidence,),
        discoveries=(discovery,),
        data_profile=profile,
    )

    assert context.active_plan is active_plan
    assert context.objective is objective
    assert context.assumptions == (assumption,)
    assert context.hypotheses == (hypothesis,)
    assert context.evidences == (evidence,)
    assert context.discoveries == (discovery,)
    assert context.data_profile is profile
    assert "tasks" not in PlannerContext.model_fields
    assert "conversation_history" not in PlannerContext.model_fields
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PlannerContext(tasks=(task,))  # type: ignore[call-arg]


def test_response_candidate_plan_and_human_input_request_are_valid() -> None:
    objective = Objective(text="Understand customer retention.")
    task = _task(objective)
    plan = _plan(objective, (task,))

    assert PlannerResult(response="The admitted evidence answers this.").plan is None
    candidate = PlannerResult(
        plan=plan,
        response="I propose this bounded investigation.",
    )
    assert candidate.plan is plan
    assert candidate.plan.tasks == (task,)
    assert PlannerResult(human_input_request="Which cohort is in scope?").plan is None


def test_candidate_cannot_be_generated_and_authorized_in_same_result() -> None:
    objective = Objective(text="Understand customer retention.")
    task = _task(objective)

    with pytest.raises(ValidationError, match="candidate Plan"):
        PlannerResult(
            plan=_plan(objective, (task,)),
            continue_execution=True,
        )
    with pytest.raises(ValidationError, match="Human input request"):
        PlannerResult(
            human_input_request="Confirm the cohort.",
            continue_execution=True,
        )


def test_discard_signal_has_exact_structural_conflicts() -> None:
    objective = Objective(text="Understand customer retention.")
    task = _task(objective)
    plan = _plan(objective, (task,))

    assert PlannerResult(discard_candidate=True).discard_candidate is True
    assert PlannerResult(
        response="Discarded the proposal.",
        discard_candidate=True,
    ).response == "Discarded the proposal."
    with pytest.raises(ValidationError, match="new candidate Plan"):
        PlannerResult(plan=plan, discard_candidate=True)
    with pytest.raises(ValidationError, match="continue_execution"):
        PlannerResult(continue_execution=True, discard_candidate=True)
    with pytest.raises(ValidationError, match="Human input request"):
        PlannerResult(
            human_input_request="Which proposal?",
            discard_candidate=True,
        )


def test_empty_result_is_rejected() -> None:
    with pytest.raises(ValidationError, match="meaningful conclusion"):
        PlannerResult()


def test_model_visible_contracts_exclude_execution_routing() -> None:
    visible_fields = set(PlannerContext.model_fields) | set(PlannerResult.model_fields)
    result_schema = str(PlannerResult.model_json_schema())

    for forbidden in (
        "Capability",
        "dispatcher",
        "provider",
        "executor",
        "worker",
        "selected_capability",
        "created_assumption",
    ):
        assert forbidden not in visible_fields
        assert forbidden not in result_schema
