from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from cognieda.agents.planner.context import PlannerContext
from cognieda.agents.planner.types import PlannerOutput, PlannerResult
from cognieda.runtime.conversation import ConversationHistory
from cognieda.schemas import (
    Assumption,
    DataProfile,
    Discovery,
    DiscoveryClaim,
    Evidence,
    EvidenceProvenance,
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
    return Plan.create(
        objective=objective,
        task_ids=(task.task_id for task in tasks),
        tasks=tasks,
    )


def _evidence_and_discovery(
    task: Task,
    profile: DataProfile,
) -> tuple[Evidence, Discovery]:
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
    hypothesis_id = uuid4()
    discovery = Discovery(
        hypothesis_id=hypothesis_id,
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
            hypothesis_id=hypothesis_id,
            evidence_ids=[evidence.evidence_id],
            method="complete count",
            decision_rule="Support when missing count equals zero.",
        ),
    )
    return evidence, discovery


def test_planner_context_and_result_have_exact_canonical_fields() -> None:
    assert tuple(PlannerContext.model_fields) == (
        "active_plan",
        "objective",
        "assumptions",
        "tasks",
        "evidences",
        "discoveries",
        "data_profile",
        "conversation_history",
    )
    assert tuple(PlannerResult.model_fields) == (
        "plan",
        "tasks",
        "response",
        "human_input_request",
        "continue_execution",
    )
    assert tuple(PlannerOutput.model_fields) == ("result", "messages", "error")


def test_planner_context_retains_all_typed_readable_state() -> None:
    objective = Objective(text="Understand customer retention.")
    assumption = Assumption(text="Rows represent customers.")
    task = _task(objective)
    profile = DataProfile(row_count=10, column_count=0, columns=())
    evidence, discovery = _evidence_and_discovery(task, profile)
    active_plan = _plan(objective, (task,))
    history = ConversationHistory()

    context = PlannerContext(
        active_plan=active_plan,
        objective=objective,
        assumptions=(assumption,),
        tasks=(task,),
        evidences=(evidence,),
        discoveries=(discovery,),
        data_profile=profile,
        conversation_history=history,
    )

    assert context.active_plan is active_plan
    assert context.objective is objective
    assert context.assumptions == (assumption,)
    assert context.tasks == (task,)
    assert context.evidences == (evidence,)
    assert context.discoveries == (discovery,)
    assert context.data_profile is profile
    assert context.conversation_history is history


def test_response_candidate_plan_and_human_input_request_are_valid() -> None:
    objective = Objective(text="Understand customer retention.")
    task = _task(objective)
    plan = _plan(objective, (task,))

    assert PlannerResult(response="The admitted evidence answers this.").plan is None
    candidate = PlannerResult(
        plan=plan,
        tasks=(task,),
        response="I propose this bounded investigation.",
    )
    assert candidate.plan is plan
    assert candidate.tasks == (task,)
    assert PlannerResult(human_input_request="Which cohort is in scope?").plan is None


def test_tasks_without_plan_are_rejected() -> None:
    objective = Objective(text="Understand customer retention.")

    with pytest.raises(ValidationError, match="tasks require"):
        PlannerResult(tasks=(_task(objective),))


def test_plan_must_validate_the_exact_task_bundle() -> None:
    objective = Objective(text="Understand customer retention.")
    expected = _task(objective, "Expected task")
    unexpected = _task(objective, "Unexpected task")
    plan = _plan(objective, (expected,))

    with pytest.raises(ValidationError, match="exactly match"):
        PlannerResult(plan=plan, tasks=(unexpected,))


def test_continue_execution_rejects_candidate_plan_or_human_input_request() -> None:
    objective = Objective(text="Understand customer retention.")
    task = _task(objective)

    with pytest.raises(ValidationError, match="candidate Plan"):
        PlannerResult(
            plan=_plan(objective, (task,)),
            tasks=(task,),
            continue_execution=True,
        )
    with pytest.raises(ValidationError, match="Human input request"):
        PlannerResult(
            human_input_request="Confirm the cohort.",
            continue_execution=True,
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
