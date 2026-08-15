from __future__ import annotations

import asyncio
from collections.abc import Sequence
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
from cognieda.agents.planner.model import PlannerModelResult
from cognieda.agents.planner.types import (
    PlannerAction,
    PlannerAnswerInput,
    PlannerControlledError,
    PlannerDecision,
    PlannerErrorCode,
    PlannerModelInput,
    PlannerOutput,
    PlannerResponseDraft,
)
from cognieda.application.ports import AgentFactoryPort
from cognieda.execution import ExecutionRequest, ExecutorDispatcher
from cognieda.runtime.application import Application
from cognieda.runtime.conversation import ConversationHistory, ConversationTurn
from cognieda.runtime.messages import ErrorEvent, StatusEvent
from cognieda.runtime.workspace import Workspace


def _messages(request: str, response: str) -> tuple[ModelMessage, ...]:
    return (
        ModelRequest(parts=[UserPromptPart(content=request)]),
        ModelResponse(parts=[TextPart(content=response)]),
    )


class NeverDispatcher:
    async def dispatch(self, request: ExecutionRequest):
        raise AssertionError(f"Unexpected dispatch: {request}")


class SequencePlannerModel:
    def __init__(self, *decisions: PlannerDecision) -> None:
        self._decisions = iter(decisions)
        self.message_histories: list[tuple[ModelMessage, ...]] = []

    async def decide(
        self,
        model_input: PlannerModelInput,
        *,
        message_history: Sequence[ModelMessage] = (),
    ) -> PlannerModelResult[PlannerDecision]:
        self.message_histories.append(tuple(message_history))
        return PlannerModelResult(
            output=next(self._decisions),
            new_messages=_messages(model_input.latest_request, "typed decision"),
        )

    async def answer(
        self, answer_input: PlannerAnswerInput
    ) -> PlannerModelResult[PlannerResponseDraft]:
        raise AssertionError(f"Unexpected answer request: {answer_input}")


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
    model = SequencePlannerModel(
        PlannerDecision(
            action=PlannerAction.SET_OR_REFINE_OBJECTIVE,
            objective_text="Understand customer churn.",
        ),
        PlannerDecision(action=PlannerAction.STATE_SUMMARY),
    )
    dispatcher = NeverDispatcher()
    planner = Planner(
        deps=PlannerDeps(dispatcher=dispatcher),
        planner_model=model,
    )
    application = Application(
        workspace=cast(Workspace, object()),
        planner_agent=planner,
        dispatcher=cast(ExecutorDispatcher, dispatcher),
        agent_factory=cast(AgentFactoryPort, object()),
    )

    async def first_turn_events() -> list[object]:
        return [
            event async for event in application.submit_message("Investigate customer churn.")
        ]

    asyncio.run(first_turn_events())
    first_turn = application.conversation_history.turns[0]

    async def second_turn_events() -> list[object]:
        return [
            event async for event in application.submit_message("Summarize what we established.")
        ]

    events = asyncio.run(second_turn_events())

    assert application.session_frame.objective is not None
    assert application.session_frame.objective.text == "Understand customer churn."
    assert model.message_histories == [(), first_turn.messages]
    assert len(application.conversation_history.turns) == 2
    assert "Understand customer churn." in events[-1].content


def test_skill_assignment_preserves_runtime_reload_path_without_planner_state_access() -> None:
    workspace = Mock(spec=Workspace)
    workspace.project_config = Mock()
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

    async def command_events() -> list[object]:
        return [
            event async for event in application.submit_message("/skill assign planner review")
        ]

    events = asyncio.run(command_events())

    workspace.add_worker_skill.assert_called_once_with("planner", "review")
    agent_factory.reload_tooling.assert_called_once_with()
    planner.reload.assert_awaited_once_with(
        model_config=None,
        agent_instruction=None,
        recreate_agent=True,
    )
    planner.run.assert_not_called()
    assert application.session_frame is original_frame
    assert len(events) == 1
    assert events[0].content == "Assigned 'review' to 'planner'."


def test_application_surfaces_planner_controlled_failure_as_error_event() -> None:
    workspace = Mock(spec=Workspace)
    planner = Mock(spec=Planner)
    planner.run = AsyncMock(
        return_value=PlannerOutput(
            response="Planner could not produce a valid typed decision: Planner model configuration has not been configured.",
            error=PlannerControlledError(
                code=PlannerErrorCode.INVALID_MODEL_DECISION,
                message="Planner could not produce a valid typed decision: Planner model configuration has not been configured.",
            ),
        )
    )
    application = Application(
        workspace=workspace,
        planner_agent=planner,
        dispatcher=cast(ExecutorDispatcher, object()),
        agent_factory=cast(AgentFactoryPort, object()),
    )

    async def turn_events() -> list[object]:
        return [event async for event in application.submit_message("hello")]

    events = asyncio.run(turn_events())

    assert events[0] == StatusEvent("Planning...")
    assert events[1] == ErrorEvent(
        "Planner could not produce a valid typed decision: Planner model configuration has not been configured."
    )
