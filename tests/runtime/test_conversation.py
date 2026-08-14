from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Any, cast
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
from cognieda.agents.planner.context import PlannerContext
from cognieda.agents.planner.types import PlannerOutput, PlannerResult
from cognieda.application.ports import AgentFactoryPort
from cognieda.delegation import ExecutorDispatcher
from cognieda.runtime.application import Application
from cognieda.runtime.conversation import ConversationHistory, ConversationTurn
from cognieda.runtime.workspace import Workspace
from cognieda.schemas import Objective, Plan, Task, TaskKind


def _messages(request: str, response: str) -> tuple[ModelMessage, ...]:
    return (
        ModelRequest(parts=[UserPromptPart(content=request)]),
        ModelResponse(parts=[TextPart(content=response)]),
    )


class SequencePlanner:
    def __init__(self, outputs: Iterable[PlannerOutput]) -> None:
        self._outputs = iter(outputs)
        self.requests: list[str] = []
        self.contexts: list[PlannerContext] = []

    async def run(self, request: str, *, context: PlannerContext) -> PlannerOutput:
        self.requests.append(request)
        self.contexts.append(context)
        return next(self._outputs)

    async def reload(self, **_: Any) -> None:
        pass


def _candidate_result() -> PlannerResult:
    objective = Objective(text="Understand customer churn.")
    task = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="Profile churn labels.",
    )
    plan = Plan.create(
        objective=objective,
        task_ids=(task.task_id,),
        tasks=(task,),
    )
    return PlannerResult(
        plan=plan,
        tasks=(task,),
        response="I propose a bounded investigation.",
    )


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


def test_application_retains_messages_but_does_not_admit_candidate_plan() -> None:
    first_messages = _messages("Investigate churn.", "Proposed a plan.")
    second_messages = _messages("Summarize.", "No plan has been admitted.")
    planner = SequencePlanner(
        (
            PlannerOutput(result=_candidate_result(), messages=first_messages),
            PlannerOutput(
                result=PlannerResult(response="No plan has been admitted."),
                messages=second_messages,
            ),
        )
    )
    application = Application(
        workspace=cast(Workspace, object()),
        planner_agent=cast(Planner, planner),
        dispatcher=cast(ExecutorDispatcher, object()),
        agent_factory=cast(AgentFactoryPort, object()),
    )

    first = asyncio.run(application.submit_message("Investigate churn."))
    second = asyncio.run(application.submit_message("Summarize."))

    assert first.content == "I propose a bounded investigation."
    assert second.content == "No plan has been admitted."
    assert application.session_frame.objective is None
    assert application.session_frame.tasks == ()
    assert len(application.conversation_history.turns) == 2
    assert planner.contexts[0].conversation_history.turns == ()
    assert planner.contexts[1].conversation_history.turns[0].messages == first_messages


def test_skill_assignment_reloads_tooling_and_planner_without_state_mutation() -> None:
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
