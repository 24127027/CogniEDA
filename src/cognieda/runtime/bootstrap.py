from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from cognieda.agents.data_explorer import DataExplorer
from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.dependencies import PlannerDeps
from cognieda.application.services import PlanAdmissionService
from cognieda.delegation import ExecutorDispatcher, ExecutorRegistry
from cognieda.infrastructure.llm import AgentFactory
from cognieda.infrastructure.persistence import get_session, init_db
from cognieda.infrastructure.persistence.repositories import ActivePlanRepository

from .application import Application
from .event_bus import EventBus
from .planner_context import PlannerContextProvider, SessionFrameState
from .workspace import MissingModelCredentialError, Workspace


def _load_workspace_environment(workspace_path: Path) -> None:
    env_path = workspace_path.expanduser().resolve() / ".env"
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.touch(exist_ok=True)
    load_dotenv(dotenv_path=env_path, override=False)


def bootstrap_application(workspace_path: Path) -> Application:
    _load_workspace_environment(workspace_path)
    workspace = Workspace.open(workspace_path)

    try:
        model_config = workspace.project_config.resolve_model()
    except MissingModelCredentialError:
        model_config = None

    agent_factory = AgentFactory(tooling_config=workspace)

    registry = ExecutorRegistry()
    registry.register(
        lambda: DataExplorer(
            config=model_config,
            agent_factory=agent_factory if model_config is not None else None,
        ),
    )
    dispatcher = ExecutorDispatcher(registry)
    database_url = init_db()
    session = get_session(database_url)
    session_frame_state = SessionFrameState()
    planner_context_provider = PlannerContextProvider(
        session_frame_provider=session_frame_state,
        active_plans=ActivePlanRepository(session),
    )
    planner = Planner(
        deps=PlannerDeps(dispatcher=dispatcher),
        agent_factory=agent_factory,
        model_config=model_config,
        planner_context_provider=planner_context_provider,
        plan_admission=PlanAdmissionService(session),
        agent_instruction=workspace.load_agent_instruction(),
    )
    event_bus = EventBus()

    return Application(
        agent_factory=agent_factory,
        workspace=workspace,
        planner_agent=planner,
        event_bus=event_bus,
        session_frame_state=session_frame_state,
    )
