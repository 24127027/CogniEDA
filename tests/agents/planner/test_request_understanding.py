from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest
from pydantic import TypeAdapter, ValidationError
from pydantic_ai.messages import ModelMessage

from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.contracts import (
    AnswerFromContextDecision,
    AssumptionAssessmentDecision,
    PlannerAction,
    PlannerDecision,
    PlannerErrorCode,
    SetOrRefineObjectiveDecision,
    StateSummaryDecision,
    UnsupportedDecision,
)
from cognieda.application.ports import ModelConfig
from cognieda.runtime.conversation import ConversationHistory
from cognieda.runtime.planner_context import build_planner_context
from cognieda.schemas.artifacts import Assumption, Objective, SessionFrame, Task
from cognieda.schemas.enums import TaskKind


@dataclass
class FakeRunResult:
    output: object

    def new_messages(self) -> list[ModelMessage]:
        return []


class RecordingPlannerAgent:
    def __init__(self, decision: PlannerDecision) -> None:
        self.decision = decision
        self.calls: list[dict[str, object]] = []

    async def run(self, prompt: str, **kwargs: object) -> FakeRunResult:
        self.calls.append({"prompt": prompt, **kwargs})
        return FakeRunResult(output=self.decision)


class FakeAgentFactory:
    def __init__(self, agent: RecordingPlannerAgent) -> None:
        self.agent = agent

    def create_agent(self, **_: object) -> RecordingPlannerAgent:
        return self.agent

    def reload_tooling(self) -> None:
        pass


def _planner(agent: RecordingPlannerAgent) -> Planner:
    return Planner(
        agent_factory=FakeAgentFactory(agent),  # type: ignore[arg-type]
        model_config=ModelConfig(provider="openai", model_name="test", api_key="test"),
    )


def _run(
    planner: Planner,
    request: str,
    frame: SessionFrame | None = None,
    history: ConversationHistory | None = None,
):
    return asyncio.run(
        planner.run(
            request,
            planner_context=build_planner_context(frame or SessionFrame()),
            conversation_history=history or ConversationHistory(),
        )
    )


def test_understanding_uses_request_and_exact_context_without_flattening_dto() -> None:
    objective = Objective(text="Understand customer retention.")
    assumption = Assumption(text="Rows represent customers.")
    task = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="Profile the active dataset.",
    )
    frame = SessionFrame(objective=objective, assumptions=(assumption,), tasks=(task,))
    model = RecordingPlannerAgent(StateSummaryDecision())

    output = _run(_planner(model), "Summarize the active state.", frame)

    assert isinstance(output.decision, StateSummaryDecision)
    assert output.objective_proposal is None
    assert output.assumption_assessment is None
    prompt = str(model.calls[0]["prompt"])
    assert "Current Human request:\nSummarize the active state." in prompt
    assert str(objective.objective_id) in prompt
    assert assumption.text in prompt
    assert task.instruction in prompt
    assert "PlannerDecisionInput" not in prompt


def test_explicit_and_model_objective_requests_use_canonical_objective_payload() -> None:
    natural_objective = Objective(text="Understand customer churn.")
    natural = _run(
        _planner(
            RecordingPlannerAgent(
                SetOrRefineObjectiveDecision(objective=natural_objective)
            )
        ),
        "Investigate customer churn.",
    )
    explicit = _run(
        _planner(RecordingPlannerAgent(StateSummaryDecision())),
        "/objective Understand customer churn.",
    )

    assert natural.objective_proposal is natural_objective
    assert explicit.objective_proposal is not None
    assert explicit.objective_proposal.text == natural_objective.text


@pytest.mark.parametrize("command", ["/profile data", "/analyze data", "/transform data"])
def test_legacy_data_commands_fail_controlled_without_routing(command: str) -> None:
    model = RecordingPlannerAgent(StateSummaryDecision())

    output = _run(_planner(model), command)

    assert isinstance(output.decision, UnsupportedDecision)
    assert output.error is not None
    assert output.error.code is PlannerErrorCode.UNSUPPORTED_ACTION
    assert model.calls == []


def test_unknown_explicit_command_fails_without_model_fallback() -> None:
    model = RecordingPlannerAgent(StateSummaryDecision())

    output = _run(_planner(model), "/unknown remove everything")

    assert output.error is not None
    assert output.error.code is PlannerErrorCode.INVALID_COMMAND
    assert output.objective_proposal is None
    assert output.assumption_assessment is None
    assert model.calls == []


def test_action_variants_expose_only_their_own_fields() -> None:
    assert set(AnswerFromContextDecision.model_fields) == {"action"}
    assert set(StateSummaryDecision.model_fields) == {"action"}
    assert set(SetOrRefineObjectiveDecision.model_fields) == {"action", "objective"}
    assert set(AssumptionAssessmentDecision.model_fields) == {"action", "assessment"}
    assert set(UnsupportedDecision.model_fields) == {"action", "message"}

    with pytest.raises(ValidationError):
        TypeAdapter(PlannerDecision).validate_python(
            {
                "action": PlannerAction.STATE_SUMMARY,
                "message": "unrelated payload",
            }
        )
