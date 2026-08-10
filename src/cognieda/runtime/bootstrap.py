from __future__ import annotations

import os
from pathlib import Path

from cognieda.agents.data_explorer import DataExplorer
from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.dependencies import PlannerDeps
from cognieda.application.ports import ModelConfig
from cognieda.execution import Capability, ExecutorDispatcher, ExecutorRegistry
from cognieda.infrastructure.agent_tooling import AgentTooling
from cognieda.infrastructure.llm import OpenAICompatibleAgentFactory
from cognieda.infrastructure.persistence import (
    SqlitePlannerResearchState,
    get_session,
    init_db,
)

from .application import Application
from .planner_context import PlannerContextPreparer
from .workspace import Workspace


def bootstrap_application(workspace_path: Path) -> Application:
    workspace = Workspace.open(workspace_path)
    model_config = resolve_model_config(workspace)
    config_root = workspace.root / ".cognieda"
    tooling = AgentTooling.from_config_path(
        path=config_root / "agents.toml",
        mcp_path=config_root / "mcp.toml",
        skills_path=config_root / "skills.toml",
    )
    agent_factory = OpenAICompatibleAgentFactory(tooling)

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
    database_url = f"sqlite:///{(workspace.state_dir / 'cognieda.sqlite3').as_posix()}"
    init_db(database_url)
    research_state = SqlitePlannerResearchState(get_session(database_url))
    planner = Planner(
        deps=PlannerDeps(dispatcher=dispatcher, state_mutations=research_state),
        agent_factory=agent_factory,
        model_config=model_config,
    )

    return Application(
        workspace=workspace,
        planner_agent=planner,
        planner_context_preparer=PlannerContextPreparer(research_state),
        dispatcher=dispatcher,
    )


def _resolved_value(workspace: Workspace, key: str, environment_name: str) -> str:
    workspace_value = workspace.config.get(key)
    if workspace_value is not None and str(workspace_value).strip():
        return str(workspace_value)
    return os.environ.get(environment_name, "").strip()


def resolve_model_config(workspace: Workspace) -> ModelConfig:
    """Resolve workspace-first model configuration without mutating process state."""

    model_name = _resolved_value(workspace, "model.name", "COGNIEDA_MODEL_NAME")
    base_url = _resolved_value(workspace, "model.base_url", "COGNIEDA_OPENAI_BASE_URL")
    api_key = _resolved_value(workspace, "model.api_key", "COGNIEDA_OPENAI_API_KEY")

    if not model_name:
        raise ValueError("Model name is required in .cognieda/project.toml or COGNIEDA_MODEL_NAME.")
    if not api_key:
        raise ValueError(
            "Model API key is required in .cognieda/project.toml or COGNIEDA_OPENAI_API_KEY."
        )

    return ModelConfig(model_name=model_name, base_url=base_url, api_key=api_key)
