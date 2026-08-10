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


def test_planner_model_uses_native_history_and_current_typed_run_instructions() -> None:
    new_messages: tuple[ModelMessage, ...] = (
        ModelRequest(parts=[UserPromptPart(content="Current request")]),
        ModelResponse(parts=[TextPart(content="Current response")]),
    )
    decision = PlannerDecision(action=PlannerAction.STATE_SUMMARY)
    message_history: tuple[ModelMessage, ...] = (
        ModelRequest(
            parts=[UserPromptPart(content="Earlier request")],
            instructions='Current typed input: {"objective":"stale"}',
        ),
        ModelResponse(parts=[TextPart(content="Earlier response")]),
    )
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
            ),
            message_history=message_history,
        )
    )

    assert result.output == decision
    assert result.new_messages == new_messages
    assert agent.calls[0]["prompt"] == "Summarize what we established."
    assert agent.calls[0]["message_history"] == message_history
    assert "message_history" in inspect.signature(PlannerModel.decide).parameters
    instructions = str(agent.calls[0]["instructions"])
    assert "Summarize what we established." in instructions
    assert "current typed input supersedes" in instructions
    assert "stale" not in instructions
    assert "Conversation history is non-authoritative" in instructions
    assert "conversation" not in PlannerModelInput.model_fields
    assert "surface_discourse" not in PlannerModelInput.model_fields
