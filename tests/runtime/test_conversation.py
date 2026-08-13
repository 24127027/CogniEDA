from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import ValidationError
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.dependencies import PlannerDeps
from cognieda.agents.planner.types import (
    PlannerAction,
    PlannerDecision,
    PlannerDecisionInput,
)
from cognieda.application.ports import AgentFactoryPort, ModelConfig
from cognieda.execution import ExecutionRequest, ExecutorDispatcher
from cognieda.runtime.application import Application
from cognieda.runtime.conversation import ConversationHistory, ConversationTurn
from cognieda.runtime.workspace import Workspace


def _messages(request: str, response: str) -> tuple[ModelMessage, ...]:
    return (
        ModelRequest(parts=[UserPromptPart(content=request)]),
        ModelResponse(parts=[TextPart(content=response)]),
    )


class NeverDispatcher:
    async def dispatch(self, request: ExecutionRequest):
        raise AssertionError(f"Unexpected dispatch: {request}")


@dataclass
class FakeRunResult:
    output: object
    messages: tuple[ModelMessage, ...]

    def new_messages(self) -> list[ModelMessage]:
        return list(self.messages)


class SequencePlannerAgent:
    def __init__(self, *decisions: PlannerDecision) -> None:
        self._decisions = iter(decisions)
        self.message_histories: list[tuple[ModelMessage, ...]] = []

    async def run(self, prompt: str, **kwargs: object) -> FakeRunResult:
        assert kwargs["output_type"] is PlannerDecision
        model_input = PlannerDecisionInput.model_validate_json(prompt.split("\n", 1)[1])
        history = kwargs.get("message_history", ())
        self.message_histories.append(tuple(history))  # type: ignore[arg-type]
        return FakeRunResult(
            output=next(self._decisions),
            messages=_messages(model_input.latest_request, "typed decision"),
        )


class FakeAgentFactory:
    def __init__(self, agent: SequencePlannerAgent) -> None:
        self.agent = agent

    def create_agent(self, **_: object) -> SequencePlannerAgent:
        return self.agent

    def reload_tooling(self) -> None:
        pass


def test_conversation_history_appends_complete_native_message_turns() -> None:
    first_messages = _messages("First request", "First response")
    second_messages = _messages("Second request", "Second response")

    empty = ConversationHistory()
    first = empty.add_turn(first_messages)
    second = first.add_turn(second_messages)

    assert empty.turns == ()
    assert first.turns[0].messages == first_messages
    assert second.model_messages() == [*first_messages, *second_messages]
    with pytest.raises(ValidationError, match="at least one ModelMessage"):
        ConversationTurn(messages=())


def test_application_retains_original_history_alongside_current_session_frame() -> None:
    model = SequencePlannerAgent(
        PlannerDecision(
            action=PlannerAction.SET_OR_REFINE_OBJECTIVE,
            objective_text="Understand customer churn.",
        ),
        PlannerDecision(action=PlannerAction.STATE_SUMMARY),
    )
    dispatcher = NeverDispatcher()
    planner = Planner(
        deps=PlannerDeps(dispatcher=dispatcher),
        agent_factory=FakeAgentFactory(model),  # type: ignore[arg-type]
        model_config=ModelConfig(provider="openai", model_name="test", api_key="test"),
    )
    application = Application(
        workspace=cast(Workspace, object()),
        planner_agent=planner,
        dispatcher=cast(ExecutorDispatcher, dispatcher),
        agent_factory=cast(AgentFactoryPort, object()),
    )

    asyncio.run(application.submit_message("Investigate customer churn."))
    first_turn = application.conversation_history.turns[0]
    asyncio.run(application.submit_message("Summarize what we established."))

    assert application.session_frame.objective is not None
    assert application.session_frame.objective.text == "Understand customer churn."
    assert model.message_histories == [(), first_turn.messages]
    assert len(application.conversation_history.turns) == 2


def test_skill_assignment_preserves_runtime_reload_path_without_planner_state_access() -> None:
    workspace = Mock(spec=Workspace)
    planner = Mock(spec=Planner)
    planner.reload = AsyncMock()
    agent_factory = Mock()
    application = Application(
        workspace=workspace,
        planner_agent=planner,
        dispatcher=cast(ExecutorDispatcher, object()),
        agent_factory=cast(AgentFactoryPort, agent_factory),
    )
    original_frame = application.session_frame

    response = asyncio.run(application.submit_message("/skill assign planner review"))

    workspace.add_worker_skill.assert_called_once_with("planner", "review")
    agent_factory.reload_tooling.assert_called_once_with()
    planner.reload.assert_awaited_once_with(recreate_agent=True)
    planner.run.assert_not_called()
    assert application.session_frame is original_frame
    assert response.content == "Assigned skill 'review' to 'planner'."
