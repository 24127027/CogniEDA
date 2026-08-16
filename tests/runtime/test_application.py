from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable
from typing import cast
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart

from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.context import PlannerContext
from cognieda.agents.planner.state import PlannerTurnOutcome
from cognieda.agents.planner.types import PlannerControlledError, PlannerErrorCode
from cognieda.application.ports import AgentFactoryPort
from cognieda.runtime.application import Application
from cognieda.runtime.conversation import ConversationHistory, ConversationSegment
from cognieda.runtime.event_bus import EventBus
from cognieda.runtime.events import (
    HumanInputRequested,
    MessageProduced,
    PlanProposed,
    RuntimeEvent,
)
from cognieda.runtime.workspace import Workspace
from cognieda.schemas import Objective, Plan, Task, TaskKind


def _candidate() -> Plan:
    objective = Objective(text="Understand customer churn.")
    task = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="Profile churn labels.",
    )
    return Plan(objective=objective, tasks=(task,))


def _application(
    planner: Planner,
    *,
    workspace: Workspace | None = None,
    agent_factory: AgentFactoryPort | None = None,
    session_id: UUID | None = None,
    conversation_history: ConversationHistory | None = None,
    planner_context_factory: Callable[[], PlannerContext] | None = None,
) -> tuple[Application, list[RuntimeEvent]]:
    event_bus = EventBus()
    events: list[RuntimeEvent] = []
    event_bus.subscribe(MessageProduced, events.append)
    event_bus.subscribe(PlanProposed, events.append)
    event_bus.subscribe(HumanInputRequested, events.append)
    application = Application(
        workspace=workspace or cast(Workspace, object()),
        planner_agent=planner,
        agent_factory=agent_factory or cast(AgentFactoryPort, object()),
        event_bus=event_bus,
        session_id=session_id or uuid4(),
        conversation_history=conversation_history or ConversationHistory(),
        planner_context_factory=(
            planner_context_factory or Mock(return_value=Mock(spec=PlannerContext))
        ),
    )
    return application, events


def test_application_maps_planner_outcome_to_presentation_events() -> None:
    plan = _candidate()
    planner = Mock(spec=Planner)
    planner.handle_message = AsyncMock(
        return_value=(
            PlannerTurnOutcome(
                proposed_plan=plan,
                response="I propose a bounded investigation.",
                human_input_request="Does this scope look right?",
            ),
            (),
        )
    )
    planner_context_factory = Mock(return_value=Mock(spec=PlannerContext))
    application, events = _application(
        planner,
        planner_context_factory=planner_context_factory,
    )

    asyncio.run(application.submit_message("Investigate churn."))

    planner.handle_message.assert_awaited_once_with(
        "Investigate churn.",
        context=planner_context_factory.return_value,
        message_history=(),
    )
    assert [type(event) for event in events] == [
        PlanProposed,
        MessageProduced,
        HumanInputRequested,
    ]
    assert cast(PlanProposed, events[0]).plan == plan
    assert cast(MessageProduced, events[1]).message.content == (
        "I propose a bounded investigation."
    )
    assert cast(HumanInputRequested, events[2]).message.content == (
        "Does this scope look right?"
    )


def test_application_maps_controlled_planner_failure_to_error_event() -> None:
    planner = Mock(spec=Planner)
    error = PlannerControlledError(
        code=PlannerErrorCode.PLAN_ADMISSION_FAILED,
        message="The proposed Plan could not be admitted.",
    )
    planner.handle_message = AsyncMock(
        return_value=(PlannerTurnOutcome(error=error), ())
    )
    application, events = _application(planner)

    asyncio.run(application.submit_message("Proceed."))

    assert len(events) == 1
    event = cast(MessageProduced, events[0])
    assert event.message.type.value == "error"
    assert event.message.content == error.message


def test_application_has_no_concrete_repositories_or_session_frame_authority() -> None:
    constructor_parameters = inspect.signature(Application).parameters

    assert "session_id" in constructor_parameters
    assert "conversation_history" in constructor_parameters
    assert "planner_context_factory" in constructor_parameters
    assert "session_frames" not in constructor_parameters
    assert "active_plans" not in constructor_parameters
    assert not hasattr(Application, "session_frame")
    assert not hasattr(Application, "review_plan")
    assert not hasattr(Application, "_apply_planner_result")
    assert not hasattr(Application, "conversation_history")
    assert not hasattr(Application, "planner_runtime")


def test_application_commits_returned_completed_segment_to_session() -> None:
    planner = Mock(spec=Planner)
    segment = ConversationSegment(
        messages=(
            ModelRequest(parts=[UserPromptPart(content="Hello")]),
            ModelResponse(parts=[TextPart(content="World")]),
        )
    )
    planner.handle_message = AsyncMock(
        return_value=(
            PlannerTurnOutcome(response="World"),
            (segment,),
        )
    )
    conversation_history = ConversationHistory()
    application, events = _application(planner, conversation_history=conversation_history)

    assert application.conversation_history.model_messages() == []

    asyncio.run(application.submit_message("Hello"))

    assert application.conversation_history.model_messages() == list(segment.messages)
    assert len(application.conversation_history.turns) == 1
    assert application.conversation_history.turns[0].segments == (segment,)


def test_application_multiple_submit_messages_remain_in_same_chat_session() -> None:
    planner = Mock(spec=Planner)
    seg1 = ConversationSegment(
        messages=(
            ModelRequest(parts=[UserPromptPart(content="First")]),
            ModelResponse(parts=[TextPart(content="Ans1")]),
        )
    )
    seg2 = ConversationSegment(
        messages=(
            ModelRequest(parts=[UserPromptPart(content="Second")]),
            ModelResponse(parts=[TextPart(content="Ans2")]),
        )
    )
    planner.handle_message = AsyncMock(
        side_effect=[
            (PlannerTurnOutcome(response="Ans1"), (seg1,)),
            (PlannerTurnOutcome(response="Ans2"), (seg2,)),
        ]
    )
    conversation_history = ConversationHistory()
    application, _ = _application(planner, conversation_history=conversation_history)

    asyncio.run(application.submit_message("First"))
    asyncio.run(application.submit_message("Second"))

    assert planner.handle_message.await_count == 2
    assert application.conversation_history.model_messages() == [*seg1.messages, *seg2.messages]
    assert len(application.conversation_history.turns) == 2


def test_application_commits_multiple_completed_segments_as_single_turn() -> None:
    planner = Mock(spec=Planner)
    seg1 = ConversationSegment(
        messages=(
            ModelRequest(parts=[UserPromptPart(content="First request")]),
            ModelResponse(parts=[TextPart(content="First internal step")]),
        )
    )
    seg2 = ConversationSegment(
        messages=(
            ModelRequest(parts=[UserPromptPart(content="Second internal prompt")]),
            ModelResponse(parts=[TextPart(content="Second internal step")]),
        )
    )
    seg3 = ConversationSegment(
        messages=(
            ModelRequest(parts=[UserPromptPart(content="Third internal prompt")]),
            ModelResponse(parts=[TextPart(content="Final response")]),
        )
    )
    planner.handle_message = AsyncMock(
        return_value=(
            PlannerTurnOutcome(response="Final response"),
            (seg1, seg2, seg3),
        )
    )
    conversation_history = ConversationHistory()
    application, _ = _application(planner, conversation_history=conversation_history)

    asyncio.run(application.submit_message("Execute multi-step work."))

    assert len(application.conversation_history.turns) == 1
    turn = application.conversation_history.turns[0]
    assert turn.segments == (seg1, seg2, seg3)
    assert application.conversation_history.model_messages() == [
        *seg1.messages,
        *seg2.messages,
        *seg3.messages,
    ]


def test_application_zero_completed_segments_does_not_create_empty_turn() -> None:
    planner = Mock(spec=Planner)
    planner.handle_message = AsyncMock(
        return_value=(
            PlannerTurnOutcome(response="No model execution performed."),
            (),
        )
    )
    conversation_history = ConversationHistory()
    application, _ = _application(planner, conversation_history=conversation_history)

    asyncio.run(application.submit_message("Non-model message."))

    assert len(application.conversation_history.turns) == 0
    assert application.conversation_history.model_messages() == []


def test_application_fails_closed_when_context_factory_raises() -> None:
    planner = Mock(spec=Planner)
    planner.handle_message = AsyncMock()

    planner_context_factory = Mock()
    planner_context_factory.side_effect = RuntimeError(
        "Persistence failure while building context."
    )

    application, events = _application(
        planner,
        planner_context_factory=planner_context_factory,
    )

    asyncio.run(application.submit_message("Investigate."))

    planner.handle_message.assert_not_awaited()
    assert len(events) == 1
    event = cast(MessageProduced, events[0])
    assert event.message.type.value == "error"
    assert "Planner authoritative context could not be materialized." in event.message.content


def test_skill_assignment_reloads_tooling_and_planner() -> None:
    workspace = Mock(spec=Workspace)
    workspace.project_config = Mock()
    workspace.project_config.try_resolve_model.return_value = None
    planner = Mock(spec=Planner)
    planner.reload = AsyncMock()
    planner.handle_message = AsyncMock()
    agent_factory = Mock()
    application, events = _application(
        planner,
        workspace=workspace,
        agent_factory=cast(AgentFactoryPort, agent_factory),
    )

    asyncio.run(application.submit_message("/skill use planner review"))

    workspace.add_worker_skill.assert_called_once_with("planner", "review")
    agent_factory.reload_tooling.assert_called_once_with()
    planner.reload.assert_awaited_once_with(
        model_config=None,
        agent_instruction=None,
        recreate_agent=True,
    )
    planner.handle_message.assert_not_awaited()
    produced = [event for event in events if isinstance(event, MessageProduced)]
    assert [event.message.content for event in produced] == [
        "Assigned 'review' to 'planner'."
    ]


def test_provider_and_reload_commands_publish_user_visible_messages() -> None:
    workspace = Mock(spec=Workspace)
    provider = Mock()
    provider.model = "test-model"
    provider.api_key_configured.return_value = True
    workspace.project_config = Mock()
    workspace.project_config.default_provider = "openai"
    workspace.project_config.providers = {"openai": provider}
    workspace.load_agent_instruction.return_value = "reloaded instructions"
    planner = Mock(spec=Planner)
    planner.reload = AsyncMock()
    planner.handle_message = AsyncMock()
    application, events = _application(planner, workspace=workspace)

    asyncio.run(application.submit_message("/provider"))
    asyncio.run(application.submit_message("/reload"))

    produced = [event for event in events if isinstance(event, MessageProduced)]
    assert [event.message.content for event in produced] == [
        (
            "Current provider : openai\n"
            "        Model            : test-model\n"
            "        API key          : yes"
        ),
        "Planner instructions reloaded.",
    ]
    planner.reload.assert_awaited_once_with(
        model_config=None,
        agent_instruction="reloaded instructions",
        recreate_agent=False,
    )
