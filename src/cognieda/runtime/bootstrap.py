from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from cognieda.agents.data_explorer import DataExplorer
from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.dependencies import PlannerDeps
from cognieda.application.services import PlannerExecutionSessionFactory
from cognieda.execution import Capability, ExecutorDispatcher, ExecutorRegistry
from cognieda.infrastructure.llm import AgentFactory
from cognieda.infrastructure.persistence.init_db import init_db
from cognieda.infrastructure.persistence.session import get_session

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
    database_url = f"sqlite:///{(workspace.state_dir / 'cognieda.sqlite3').as_posix()}"
    init_db(database_url)
    session = get_session(database_url)

    try:
        model_config = workspace.project_config.resolve_model()
    except MissingModelCredentialError:
        model_config = None

    agent_factory = AgentFactory(tooling_config=workspace)

    registry = ExecutorRegistry()
    registry.register_provider(
        lambda: DataExplorer(
            config=model_config,
            agent_factory=agent_factory if model_config is not None else None,
        ),
        capabilities=(
            Capability.DATA_ANALYSIS,
            Capability.DATA_PROFILING,
            Capability.DATA_TRANSFORMATION,
        ),
    )
    dispatcher = ExecutorDispatcher(registry)
    planner = Planner(
        deps=PlannerDeps(
            dispatcher=dispatcher,
            execution_session_factory=PlannerExecutionSessionFactory(session),
        ),
        agent_factory=agent_factory,
        model_config=model_config,
        agent_instruction=workspace.load_planner_agent_instruction(),
    )

    return Application(
        agent_factory=agent_factory,
        workspace=workspace,
        planner_agent=planner,
        dispatcher=dispatcher,
        session=session,
    )

