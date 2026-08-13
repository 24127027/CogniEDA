from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest
from pydantic import ValidationError
from pydantic_ai.messages import ModelMessage

from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.contracts import (
    AssumptionAssessment,
    DirectResponse,
    ObjectiveProposal,
    PlannerCognitiveResult,
    PlannerErrorCode,
)
from cognieda.agents.planner.dependencies import PlannerDeps
from cognieda.application.ports import ModelConfig
from cognieda.runtime.conversation import ConversationHistory
from cognieda.runtime.planner_context import build_planner_context
from cognieda.schemas.artifacts import Assumption, Objective, SessionFrame, Task
from cognieda.schemas.enums import AssumptionTestability, TaskKind


@dataclass
class FakeRunResult:
    output: object

    def new_messages(self) -> list[ModelMessage]:
        return []


class RecordingPlannerAgent:
    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    async def run(self, prompt: str, **kwargs: object) -> FakeRunResult:
        self.calls.append({"prompt": prompt, **kwargs})
        return FakeRunResult(output=self.result)


class FakeAgentFactory:
    def __init__(self, agent: RecordingPlannerAgent) -> None:
        self.agent = agent

    def create_agent(self, **_: object) -> RecordingPlannerAgent:
        return self.agent

    def reload_tooling(self) -> None:
        pass


def _planner(agent: RecordingPlannerAgent) -> Planner:
    return Planner(
        PlannerDeps(),
        agent_factory=FakeAgentFactory(agent),  # type: ignore[arg-type]
        model_config=ModelConfig(provider="openai", model_name="test", api_key="test"),
    )


def _run(planner: Planner, request: str, frame: SessionFrame | None = None):
    return asyncio.run(
        planner.run(
            request,
            planner_context=build_planner_context(frame or SessionFrame()),
            conversation_history=ConversationHistory(),
        )
    )


def test_planner_turn_uses_request_and_exact_context() -> None:
    objective = Objective(text="Understand customer retention.")
    assumption = Assumption(text="Rows represent customers.")
    task = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="Profile the active dataset.",
    )
    frame = SessionFrame(objective=objective, assumptions=(assumption,), tasks=(task,))
    agent = RecordingPlannerAgent(DirectResponse(text="State summarized."))

    output = _run(_planner(agent), "Summarize the active state.", frame)

    assert output.result == DirectResponse(text="State summarized.")
    prompt = str(agent.calls[0]["prompt"])
    assert "Current Human request:\nSummarize the active state." in prompt
    assert str(objective.objective_id) in prompt
    assert assumption.text in prompt
    assert task.instruction in prompt
    assert agent.calls[0]["output_type"] == PlannerCognitiveResult


def test_typed_final_results_carry_one_semantic_representation() -> None:
    objective = Objective(text="Understand customer churn.")
    proposal = ObjectiveProposal(objective=objective, response="Objective proposed.")
    assessment = AssumptionAssessment(
        source_text="Competitor intent is unavailable to this project.",
        testability=AssumptionTestability.UNTESTABLE_IN_PROJECT,
        response="The exact Human statement may be used for planning only.",
    )

    proposal_output = _run(_planner(RecordingPlannerAgent(proposal)), "Set objective")
    assessment_output = _run(
        _planner(RecordingPlannerAgent(assessment)), assessment.source_text
    )

    assert proposal_output.result is proposal
    assert proposal_output.response == proposal.response
    assert assessment_output.result is assessment
    assert assessment_output.response == assessment.response
    assert "action" not in DirectResponse.model_fields
    assert "action" not in ObjectiveProposal.model_fields
    assert "action" not in AssumptionAssessment.model_fields


def test_result_contracts_reject_unrelated_fields() -> None:
    with pytest.raises(ValidationError):
        DirectResponse(text="Valid", action="summary")
    with pytest.raises(ValidationError):
        ObjectiveProposal(
            objective=Objective(text="Valid objective"),
            response="Proposed.",
            assessment="unrelated",
        )


def test_invalid_model_result_fails_closed_with_typed_response() -> None:
    output = _run(_planner(RecordingPlannerAgent({"unexpected": "shape"})), "Help")

    assert isinstance(output.result, DirectResponse)
    assert output.error is not None
    assert output.error.code is PlannerErrorCode.INVALID_MODEL_RESULT
    assert output.response == output.error.message


def test_empty_request_fails_before_agent_run() -> None:
    agent = RecordingPlannerAgent(DirectResponse(text="unused"))

    output = _run(_planner(agent), "   ")

    assert output.error is not None
    assert output.error.code is PlannerErrorCode.INVALID_COMMAND
    assert agent.calls == []
