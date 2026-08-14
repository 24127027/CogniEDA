from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from cognieda.agents.data_explorer import DataExplorer
from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.dependencies import PlannerDeps
from cognieda.execution import Capability, ExecutorDispatcher, ExecutorRegistry
from cognieda.infrastructure.llm import AgentFactory
from cognieda.infrastructure.persistence import get_session, init_db

from .application import Application
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
    registry.register_provider(
        lambda: DataExplorer(config=model_config, agent_factory=agent_factory),
        capabilities=(
            Capability.DATA_ANALYSIS,
            Capability.DATA_PROFILING,
            Capability.DATA_TRANSFORMATION,
        ),
    )
    dispatcher = ExecutorDispatcher(registry)
    planner = Planner(
        deps=PlannerDeps(dispatcher=dispatcher),
        agent_factory=agent_factory,
        model_config=model_config,
        agent_instruction=workspace.load_agent_instruction(),
    )

    database_url = init_db()

    return Application(
        agent_factory=agent_factory,
        workspace=workspace,
        planner_agent=planner,
        dispatcher=dispatcher,
        session=get_session(database_url),
    )

