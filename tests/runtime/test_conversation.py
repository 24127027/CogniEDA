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
from cognieda.agents.planner.contracts import PlannerCognitiveResult
from cognieda.agents.planner.dependencies import PlannerDeps
from cognieda.application.ports import AgentFactoryPort, ModelConfig
from cognieda.execution import ExecutorDispatcher, ExecutorRegistry
from cognieda.runtime.application import Application
from cognieda.runtime.conversation import ConversationHistory, ConversationTurn
from cognieda.runtime.workspace import Workspace


def _messages(request: str, response: str) -> tuple[ModelMessage, ...]:
    return (
        ModelRequest(parts=[UserPromptPart(content=request)]),
        ModelResponse(parts=[TextPart(content=response)]),
    )


@dataclass
class FakeRunResult:
    output: object
    messages: tuple[ModelMessage, ...]

    def all_messages(self) -> list[ModelMessage]:
        return list(self.messages)


class SequencePlannerAgent:
    def __init__(self, *results: PlannerCognitiveResult) -> None:
        self._results = iter(results)
        self.message_histories: list[tuple[ModelMessage, ...]] = []

    async def run(self, prompt: str, **kwargs: object) -> FakeRunResult:
        assert kwargs["output_type"] == PlannerCognitiveResult
        request = prompt.split("\n", 1)[1].split("\n\n", 1)[0]
        history = kwargs.get("message_history", ())
        self.message_histories.append(tuple(history))  # type: ignore[arg-type]
        return FakeRunResult(
            output=next(self._results),
            messages=(*history, *_messages(request, "typed result")),
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


def test_application_retains_complete_history_alongside_current_session_frame() -> None:
    model = SequencePlannerAgent(
        PlannerCognitiveResult(response="First response."),
        PlannerCognitiveResult(response="State summarized."),
    )
    dispatcher = ExecutorDispatcher(ExecutorRegistry())
    planner = Planner(
        PlannerDeps(dispatcher),
        agent_factory=FakeAgentFactory(model),  # type: ignore[arg-type]
        model_config=ModelConfig(provider="openai", model_name="test", api_key="test"),
    )
    application = Application(
        workspace=cast(Workspace, object()),
        planner_agent=planner,
        dispatcher=dispatcher,
        agent_factory=cast(AgentFactoryPort, object()),
    )

    asyncio.run(application.submit_message("Investigate customer churn."))
    first_turn = application.conversation_history.turns[0]
    asyncio.run(application.submit_message("Summarize what we established."))

    assert application.session_frame.objective is None
    assert model.message_histories == [(), first_turn.messages]
    assert len(application.conversation_history.turns) == 2


def test_skill_assignment_preserves_runtime_reload_path_without_planner_state_access() -> None:
    workspace = Mock()
    workspace.project_config.try_resolve_model.return_value = None
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

    response = asyncio.run(application.submit_message("/skill use planner review"))

    workspace.add_worker_skill.assert_called_once_with("planner", "review")
    agent_factory.reload_tooling.assert_called_once_with()
    planner.reload.assert_awaited_once_with(
        model_config=None,
        agent_instruction=None,
        recreate_agent=True,
    )
    planner.run.assert_not_called()
    assert application.session_frame is original_frame
    assert response.content == "Assigned 'review' to 'planner'."


def test_assumption_slash_syntax_cannot_bypass_planner_assessment() -> None:
    planner = Mock(spec=Planner)
    application = Application(
        workspace=cast(Workspace, object()),
        planner_agent=planner,
        dispatcher=cast(ExecutorDispatcher, object()),
        agent_factory=cast(AgentFactoryPort, object()),
    )
    original_frame = application.session_frame

    response = asyncio.run(
        application.submit_message("/assumption Customer age predicts churn.")
    )

    planner.run.assert_not_called()
    assert application.session_frame is original_frame
    assert application.session_frame.assumptions == ()
    assert response.content == (
        "Unknown command: '/assumption Customer age predicts churn.'."
    )


def test_skill_unassignment_reloads_tooling_and_recreates_planner_agent() -> None:
    workspace = Mock()
    workspace.project_config.try_resolve_model.return_value = None
    planner = Mock(spec=Planner)
    planner.reload = AsyncMock()
    agent_factory = Mock()
    application = Application(
        workspace=workspace,
        planner_agent=planner,
        dispatcher=cast(ExecutorDispatcher, object()),
        agent_factory=cast(AgentFactoryPort, agent_factory),
    )

    response = asyncio.run(application.submit_message("/skill drop planner review"))

    workspace.remove_worker_skill.assert_called_once_with("planner", "review")
    agent_factory.reload_tooling.assert_called_once_with()
    planner.reload.assert_awaited_once_with(
        model_config=None,
        agent_instruction=None,
        recreate_agent=True,
    )
    assert response.content == "Removed 'review' from 'planner'."


def test_reload_instructions_reads_current_workspace_planner_instruction() -> None:
    workspace = Mock(spec=Workspace)
    workspace.load_planner_agent_instruction.return_value = "current workspace guidance"
    planner = Mock(spec=Planner)
    planner.reload = AsyncMock()
    application = Application(
        workspace=workspace,
        planner_agent=planner,
        dispatcher=cast(ExecutorDispatcher, object()),
        agent_factory=cast(AgentFactoryPort, object()),
    )

    response = asyncio.run(application.submit_message("/reload"))

    workspace.load_planner_agent_instruction.assert_called_once_with()
    planner.reload.assert_awaited_once_with(
        model_config=None,
        agent_instruction="current workspace guidance",
        recreate_agent=False,
    )
    assert response.content == "Planner instructions reloaded."
