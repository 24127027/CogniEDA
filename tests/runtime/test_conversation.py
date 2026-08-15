from __future__ import annotations

import asyncio
from typing import cast
from unittest.mock import AsyncMock, Mock

from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.state import PlannerTurnOutcome
from cognieda.agents.planner.types import PlannerControlledError, PlannerErrorCode
from cognieda.application.ports import AgentFactoryPort
from cognieda.runtime.application import Application
from cognieda.runtime.bootstrap import bootstrap_application
from cognieda.runtime.event_bus import EventBus
from cognieda.runtime.events import (
    HumanInputRequested,
    MessageProduced,
    PlanProposed,
    RuntimeEvent,
)
from cognieda.runtime.planner_context import SessionFrameState
from cognieda.runtime.workspace import Workspace
from cognieda.schemas import Objective, Plan, Task, TaskKind


def _candidate() -> Plan:
    objective = Objective(text="Understand customer churn.")
    task = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="Profile churn labels.",
    )
    plan = Plan(
        objective=objective,
        tasks=(task,),
    )
    return plan


def _application(
    planner: Planner,
    *,
    workspace: Workspace | None = None,
    agent_factory: AgentFactoryPort | None = None,
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
        session_frame_state=SessionFrameState(),
    )
    return application, events


def test_application_maps_planner_outcome_to_presentation_events() -> None:
    plan = _candidate()
    planner = Mock(spec=Planner)
    planner.handle_message = AsyncMock(
        return_value=PlannerTurnOutcome(
            proposed_plan=plan,
            response="I propose a bounded investigation.",
            human_input_request="Does this scope look right?",
        )
    )
    application, events = _application(planner)

    asyncio.run(application.submit_message("Investigate churn."))

    planner.handle_message.assert_awaited_once_with("Investigate churn.")
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
        return_value=PlannerTurnOutcome(error=error)
    )
    application, events = _application(planner)

    asyncio.run(application.submit_message("Proceed."))

    assert len(events) == 1
    event = cast(MessageProduced, events[0])
    assert event.message.type.value == "error"
    assert event.message.content == error.message


def test_application_has_no_planner_lifecycle_or_history_authority() -> None:
    assert not hasattr(Application, "review_plan")
    assert not hasattr(Application, "_apply_planner_result")
    assert not hasattr(Application, "conversation_history")
    assert not hasattr(Application, "planner_runtime")


def test_bootstrap_composes_planner_before_application(
    tmp_path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "runtime.sqlite3"
    monkeypatch.setenv("COGNIEDA_DB_URL", f"sqlite:///{database_path.as_posix()}")

    application = bootstrap_application(tmp_path / "workspace")

    assert isinstance(application.planner_agent, Planner)
    assert application.planner_agent.graph is not None
    assert not hasattr(application, "planner_runtime")
    assert application.session_frame is application._session_frame_state.current


def test_skill_assignment_reloads_tooling_and_planner_without_state_mutation() -> None:
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
    original_frame = application.session_frame

    asyncio.run(application.submit_message("/skill use planner review"))

    workspace.add_worker_skill.assert_called_once_with("planner", "review")
    agent_factory.reload_tooling.assert_called_once_with()
    planner.reload.assert_awaited_once_with(
        model_config=None,
        agent_instruction=None,
        recreate_agent=True,
    )
    planner.handle_message.assert_not_awaited()
    assert application.session_frame is original_frame
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
