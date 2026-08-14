from __future__ import annotations

import inspect

import pytest
from pydantic import ValidationError

import cognieda.agents.planner.contracts as contracts
import cognieda.schemas as schemas
from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.context import PlannerContext
from cognieda.agents.planner.contracts import (
    PlannerOutput,
    PlannerResult,
)
from cognieda.runtime.conversation import ConversationHistory
from cognieda.runtime.planner_context import build_planner_context
from cognieda.schemas import (
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


def test_planner_result_model_carries_candidate_plan_bundle() -> None:
    plan, tasks = _candidate()

    result = PlannerResult(
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


def test_planner_result_rejects_contradictory_or_incomplete_shapes() -> None:
    plan, tasks = _candidate()

    with pytest.raises(ValidationError, match="Tasks require"):
        PlannerResult(tasks=tasks, response="Invalid")
    with pytest.raises(ValidationError, match="cannot also request clarification"):
        PlannerResult(
            plan=plan,
            tasks=tasks,
            human_input_request="Clarify scope.",
        )
    with pytest.raises(ValidationError, match="meaningful result"):
        PlannerResult()
    with pytest.raises(ValidationError, match="cannot also continue"):
        PlannerResult(plan=plan, tasks=tasks, continue_execution=True)
    with pytest.raises(ValidationError, match="Human clarification"):
        PlannerResult(
            human_input_request="Clarify the population.",
            continue_execution=True,
        )

    assert PlannerResult(response="Final grounded answer.").response
    assert set(PlannerResult.model_fields) == {
        "plan",
        "tasks",
        "response",
        "human_input_request",
        "continue_execution",
    }
    assert not hasattr(contracts, "PlannerCognitiveResult")
    assert "replan_reason" not in PlannerResult.model_fields


def test_planner_output_is_one_nonduplicating_envelope() -> None:
    plan, tasks = _candidate()
    result = PlannerResult(plan=plan, tasks=tasks)
    output = PlannerOutput(result=result)

    assert set(PlannerOutput.model_fields) == {"result", "messages", "error"}
    assert "plan" not in PlannerOutput.model_fields
    assert "tasks" not in PlannerOutput.model_fields
    assert output.response == "A candidate Plan is ready for Human review."


def test_public_planner_input_is_request_and_readable_context() -> None:
    parameters = inspect.signature(Planner.run).parameters

    assert tuple(parameters) == ("self", "request", "context")
    assert set(PlannerContext.model_fields) == {
        "active_plan",
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


def test_planner_result_has_no_assumption_admission_surface() -> None:
    assert not hasattr(contracts, "AssumptionAssessment")
    assert "assumption_assessment" not in PlannerResult.model_fields
    assert not hasattr(schemas, "AssumptionTestability")
