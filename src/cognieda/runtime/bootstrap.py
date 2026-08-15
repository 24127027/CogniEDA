from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from cognieda.infrastructure.llm import AgentFactory
from cognieda.agents.data_explorer import DataExplorer
from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.dependencies import PlannerDeps
from cognieda.delegation import ExecutorDispatcher, ExecutorRegistry

from .application import Application
from .workspace import MissingModelCredentialError
from .workspace import Workspace
from .event_bus import EventBus


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
        lambda: DataExplorer(config=model_config, agent_factory=agent_factory),
    )
    dispatcher = ExecutorDispatcher(registry)
    planner = Planner(
        deps=PlannerDeps(dispatcher=dispatcher),
        agent_factory=agent_factory,
        model_config=model_config,
        agent_instruction=workspace.load_agent_instruction(),
    )
    event_bus = EventBus()

    return Application(
        agent_factory=agent_factory,
        workspace=workspace,
        planner_agent=planner,
        dispatcher=dispatcher,
        event_bus=event_bus,
    )

