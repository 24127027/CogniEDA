from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest
from pydantic import ValidationError
from pydantic_ai.messages import ModelMessage

from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.dependencies import PlannerDeps
from cognieda.agents.planner.types import (
    PlannerAction,
    PlannerAnswerInput,
    PlannerDecision,
    PlannerDecisionInput,
    PlannerErrorCode,
    PlannerResponseDraft,
)
from cognieda.application.ports import ModelConfig
from cognieda.execution import ExecutionRequest
from cognieda.runtime.conversation import ConversationHistory
from cognieda.runtime.planner_context import build_planning_context
from cognieda.schemas.artifacts import Assumption, Objective, SessionFrame, Task
from cognieda.schemas.enums import TaskKind


class NeverDispatcher:
    def __init__(self) -> None:
        self.requests: list[ExecutionRequest] = []

    async def dispatch(self, request: ExecutionRequest):
        self.requests.append(request)
        raise AssertionError("This request must not dispatch executor work.")


@dataclass
class FakeRunResult:
    output: object

    def new_messages(self) -> list[ModelMessage]:
        return []


class RecordingPlannerAgent:
    def __init__(self, decision: PlannerDecision) -> None:
        self.decision = decision
        self.decision_inputs: list[PlannerDecisionInput] = []
        self.answer_inputs: list[PlannerAnswerInput] = []
        self.message_histories: list[tuple[ModelMessage, ...]] = []

    async def run(self, prompt: str, **kwargs: object) -> FakeRunResult:
        output_type = kwargs["output_type"]
        payload = prompt.split("\n", 1)[1]
        if output_type is PlannerDecision:
            self.decision_inputs.append(PlannerDecisionInput.model_validate_json(payload))
            history = kwargs.get("message_history", ())
            self.message_histories.append(tuple(history))  # type: ignore[arg-type]
            return FakeRunResult(output=self.decision)
        if output_type is PlannerResponseDraft:
            self.answer_inputs.append(PlannerAnswerInput.model_validate_json(payload))
            return FakeRunResult(output=PlannerResponseDraft(text="grounded answer"))
        raise AssertionError(f"Unexpected output type: {output_type}")


class FakeAgentFactory:
    def __init__(self, agent: RecordingPlannerAgent) -> None:
        self.agent = agent

    def create_agent(self, **_: object) -> RecordingPlannerAgent:
        return self.agent

    def reload_tooling(self) -> None:
        pass


def _planner(agent: RecordingPlannerAgent, dispatcher: NeverDispatcher) -> Planner:
    return Planner(
        deps=PlannerDeps(dispatcher=dispatcher),
        agent_factory=FakeAgentFactory(agent),  # type: ignore[arg-type]
        model_config=ModelConfig(provider="openai", model_name="test", api_key="test"),
    )


def _context(frame: SessionFrame | None = None):
    return build_planning_context(frame or SessionFrame(), ConversationHistory())


def test_natural_language_understanding_receives_latest_request_and_typed_state() -> None:
    objective = Objective(text="Understand customer retention.")
    assumption = Assumption(text="Rows represent customers.")
    task = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="Profile the active dataset.",
    )
    frame = SessionFrame(objective=objective, assumptions=(assumption,), tasks=(task,))
    model = RecordingPlannerAgent(PlannerDecision(action=PlannerAction.STATE_SUMMARY))
    dispatcher = NeverDispatcher()

    output = asyncio.run(
        _planner(model, dispatcher).run(
            "Summarize the active research state.",
            planning_context=_context(frame),
        )
    )

    assert output.decision is not None
    assert output.decision.action is PlannerAction.STATE_SUMMARY
    assert output.created_objective is None
    assert output.created_assumption is None
    assert output.created_task is None
    assert len(model.decision_inputs) == 1
    model_input = model.decision_inputs[0]
    assert model_input.latest_request == "Summarize the active research state."
    assert model_input.objective == objective
    assert model_input.assumptions == (assumption,)
    assert model_input.tasks == (task,)
    assert dispatcher.requests == []


def test_explicit_and_natural_language_objective_requests_reach_same_typed_action() -> None:
    natural_model = RecordingPlannerAgent(
        PlannerDecision(
            action=PlannerAction.SET_OR_REFINE_OBJECTIVE,
            objective_text="Understand customer churn.",
        )
    )
    explicit_model = RecordingPlannerAgent(PlannerDecision(action=PlannerAction.STATE_SUMMARY))
    dispatcher = NeverDispatcher()

    natural = asyncio.run(
        _planner(natural_model, dispatcher).run(
            "Investigate customer churn.",
            planning_context=_context(),
        )
    )
    explicit = asyncio.run(
        _planner(explicit_model, dispatcher).run(
            "/objective Understand customer churn.",
            planning_context=_context(),
        )
    )

    assert natural.decision is not None
    assert explicit.decision is not None
    assert natural.decision.action is PlannerAction.SET_OR_REFINE_OBJECTIVE
    assert explicit.decision.action is PlannerAction.SET_OR_REFINE_OBJECTIVE
    assert natural.created_objective is not None
    assert explicit.created_objective is not None
    assert natural.created_objective.text == explicit.created_objective.text
    assert explicit_model.decision_inputs == []


def test_objective_semantic_refinement_allocates_new_identity_without_mutation() -> None:
    original = Objective(text="Understand churn.")
    frame = SessionFrame(objective=original)
    model = RecordingPlannerAgent(
        PlannerDecision(
            action=PlannerAction.SET_OR_REFINE_OBJECTIVE,
            objective_text="Understand churn drivers.",
        )
    )

    output = asyncio.run(
        _planner(model, NeverDispatcher()).run(
            "Refine the objective to focus on drivers.",
            planning_context=_context(frame),
        )
    )

    assert output.created_objective is not None
    assert output.created_objective.objective_id != original.objective_id
    assert output.created_objective.text == "Understand churn drivers."
    assert original.text == "Understand churn."


def test_unknown_explicit_command_fails_without_model_fallback_or_state_change() -> None:
    frame = SessionFrame(objective=Objective(text="Keep this Objective."))
    model = RecordingPlannerAgent(PlannerDecision(action=PlannerAction.STATE_SUMMARY))
    dispatcher = NeverDispatcher()

    output = asyncio.run(
        _planner(model, dispatcher).run(
            "/unknown remove everything",
            planning_context=_context(frame),
        )
    )

    assert output.error is not None
    assert output.error.code is PlannerErrorCode.INVALID_COMMAND
    assert output.created_objective is None
    assert output.created_assumption is None
    assert output.created_task is None
    assert model.decision_inputs == []
    assert dispatcher.requests == []


def test_planner_decision_rejects_untyped_or_mixed_core_changes() -> None:
    with pytest.raises(ValidationError):
        PlannerDecision.model_validate(
            {
                "action": PlannerAction.CREATE_OR_RUN_DATA_TASK,
                "task_instruction": "Profile the dataset.",
                "capability": "not_a_capability",
            }
        )

    with pytest.raises(ValidationError):
        PlannerDecision(
            action=PlannerAction.ADD_ASSUMPTION,
            assumption_text="Rows are customers.",
            task_instruction="Profile the dataset.",
        )
