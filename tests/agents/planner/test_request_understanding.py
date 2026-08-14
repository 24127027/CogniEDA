from __future__ import annotations

import inspect

import pytest
from pydantic import ValidationError

import cognieda.agents.planner.contracts as contracts
from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.context import PlannerContext
from cognieda.agents.planner.contracts import (
    AssumptionAssessment,
    PlannerCognitiveResult,
    PlannerOutput,
)
from cognieda.runtime.conversation import ConversationHistory
from cognieda.runtime.planner_context import apply_planner_output, build_planner_context
from cognieda.schemas import (
    AssumptionTestability,
    Objective,
    Plan,
    PlanTaskBinding,
    SessionFrame,
    Task,
    TaskKind,
)


def _candidate() -> tuple[Plan, tuple[Task, ...]]:
    objective = Objective(text="Understand customer retention.")
    task = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="Profile retained customer data.",
    )
    tasks = (task,)
    plan = Plan.create(
        objective=objective,
        task_bindings=(PlanTaskBinding(task_id=task.task_id, order_rank=0),),
        tasks=tasks,
    )
    return plan, tasks


def test_one_cognitive_result_model_carries_candidate_plan_bundle() -> None:
    plan, tasks = _candidate()

    result = PlannerCognitiveResult(
        plan=plan,
        tasks=tasks,
        response="Review this complete candidate Plan.",
    )

    assert result.plan is plan
    assert result.plan.objective.text == "Understand customer retention."
    assert result.tasks == tasks
    assert not hasattr(contracts, "ObjectiveProposal")
    assert not hasattr(contracts, "DirectResponse")
    assert not hasattr(contracts, "AuthoritativeAnswerRequest")


def test_cognitive_result_rejects_contradictory_or_incomplete_shapes() -> None:
    plan, tasks = _candidate()

    with pytest.raises(ValidationError, match="Tasks require"):
        PlannerCognitiveResult(tasks=tasks, response="Invalid")
    with pytest.raises(ValidationError, match="cannot also request clarification"):
        PlannerCognitiveResult(
            plan=plan,
            tasks=tasks,
            human_input_request="Clarify scope.",
        )
    with pytest.raises(ValidationError, match="meaningful result"):
        PlannerCognitiveResult()


def test_planner_output_is_one_nonduplicating_envelope() -> None:
    plan, tasks = _candidate()
    result = PlannerCognitiveResult(plan=plan, tasks=tasks)
    output = PlannerOutput(cognitive_result=result)

    assert set(PlannerOutput.model_fields) == {"cognitive_result", "messages", "error"}
    assert "plan" not in PlannerOutput.model_fields
    assert "tasks" not in PlannerOutput.model_fields
    assert output.response == "A candidate Plan is ready for Human review."


def test_public_planner_input_is_request_and_readable_context() -> None:
    parameters = inspect.signature(Planner.run).parameters

    assert tuple(parameters) == ("self", "request", "context")
    assert set(PlannerContext.model_fields) == {
        "objective",
        "assumptions",
        "tasks",
        "evidences",
        "discoveries",
        "data_profile",
        "conversation_history",
    }


def test_context_contains_non_authoritative_conversation_history() -> None:
    history = ConversationHistory()
    frame = SessionFrame(objective=Objective(text="Read retained state."))

    context = build_planner_context(frame, history)

    assert context.objective == frame.objective
    assert context.conversation_history is history
    assert "non-authoritative" in PlannerContext.__doc__


def test_application_admits_only_exact_untestable_human_assumption() -> None:
    source = "The project cannot observe competitor intent."
    output = PlannerOutput(
        cognitive_result=PlannerCognitiveResult(
            response="This may be retained for planning only.",
            assumption_assessment=AssumptionAssessment(
                source_text=source,
                testability=AssumptionTestability.UNTESTABLE_IN_PROJECT,
            ),
        )
    )

    accepted = apply_planner_output(SessionFrame(), output, request=source)

    assert len(accepted.assumptions) == 1
    assert accepted.assumptions[0].text == source
    with pytest.raises(ValueError, match="exact Human text"):
        apply_planner_output(SessionFrame(), output, request="Paraphrased request")
