from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

from cognieda.agents.planner.context import NonAuthoritativeSurfaceTurn
from cognieda.agents.planner.dependencies import PlannerDeps
from cognieda.agents.planner.model import PlannerModel
from cognieda.agents.planner.types import (
    PlannerAction,
    PlannerDecision,
    PlannerModelInput,
)
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

    async def run(self, prompt: str, **kwargs):
        self.calls.append({"prompt": prompt, **kwargs})
        return self.result


class RecordingFactory:
    def __init__(self, agent: RecordingAgent) -> None:
        self.agent = agent

    def create_agent(self, **_):
        return self.agent


def test_planner_model_starts_fresh_execution_and_returns_exact_new_messages() -> None:
    new_messages: tuple[ModelMessage, ...] = (
        ModelRequest(parts=[UserPromptPart(content="Current request")]),
        ModelResponse(parts=[TextPart(content="Current response")]),
    )
    decision = PlannerDecision(action=PlannerAction.STATE_SUMMARY)
    agent = RecordingAgent(FakeRunResult(output=decision, messages=new_messages))
    model = PlannerModel(
        deps=PlannerDeps(
            dispatcher=object(),  # type: ignore[arg-type]
            state_mutations=object(),  # type: ignore[arg-type]
        ),
        agent_factory=RecordingFactory(agent),  # type: ignore[arg-type]
        model_config=ModelConfig(model_name="test"),
    )

    result = asyncio.run(
        model.decide(
            PlannerModelInput(
                latest_request="Summarize what we established.",
                surface_discourse=(
                    NonAuthoritativeSurfaceTurn(
                        human_message="/summary",
                        planner_response="Task T7 completed with two limitations.",
                    ),
                ),
            ),
        )
    )

    assert result.output == decision
    assert result.new_messages == new_messages
    assert "message_history" not in agent.calls[0]
    assert "message_history" not in inspect.signature(PlannerModel.decide).parameters
    prompt = str(agent.calls[0]["prompt"])
    assert "surface_discourse" in prompt
    assert "Task T7 completed with two limitations." in prompt
    assert "non-authoritative Human-Planner discourse context only" in prompt
    assert "conversation" not in PlannerModelInput.model_fields
