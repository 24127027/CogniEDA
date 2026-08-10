from __future__ import annotations

import asyncio
from dataclasses import dataclass

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

from cognieda.agents.planner.dependencies import PlannerDeps
from cognieda.agents.planner.model import PlannerModel
from cognieda.agents.planner.types import PlannerAction, PlannerDecision, PlannerModelInput
from cognieda.application.ports import ModelConfig


@dataclass
class FakeRunResult:
    output: PlannerDecision
    messages: tuple[ModelMessage, ...]

    def new_messages(self) -> list[ModelMessage]:
        return list(self.messages)


class RecordingAgent:
    def __init__(self, result: FakeRunResult) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    async def run(self, prompt: str, **kwargs: object) -> FakeRunResult:
        self.calls.append({"prompt": prompt, **kwargs})
        return self.result


class RecordingFactory:
    def __init__(self, agent: RecordingAgent) -> None:
        self.agent = agent

    def create_agent(self, **_: object) -> RecordingAgent:
        return self.agent


def test_planner_model_passes_native_history_and_returns_new_messages() -> None:
    prior_messages: tuple[ModelMessage, ...] = (
        ModelRequest(parts=[UserPromptPart(content="Earlier request")]),
        ModelResponse(parts=[TextPart(content="Earlier response")]),
    )
    new_messages: tuple[ModelMessage, ...] = (
        ModelRequest(parts=[UserPromptPart(content="Current request")]),
        ModelResponse(parts=[TextPart(content="Current response")]),
    )
    decision = PlannerDecision(action=PlannerAction.STATE_SUMMARY)
    agent = RecordingAgent(FakeRunResult(output=decision, messages=new_messages))
    model = PlannerModel(
        deps=PlannerDeps(dispatcher=object()),  # type: ignore[arg-type]
        agent_factory=RecordingFactory(agent),  # type: ignore[arg-type]
        model_config=ModelConfig(model_name="test"),
    )

    result = asyncio.run(
        model.decide(
            PlannerModelInput(latest_request="Summarize what we established."),
            message_history=prior_messages,
        )
    )

    assert result.output == decision
    assert result.new_messages == new_messages
    assert agent.calls[0]["message_history"] == list(prior_messages)
