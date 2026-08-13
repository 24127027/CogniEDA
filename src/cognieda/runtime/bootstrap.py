from __future__ import annotations

import os
from pathlib import Path

from cognieda.infrastructure.llm import AgentFactory
from cognieda.agents.data_explorer import DataExplorer
from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.dependencies import PlannerDeps
from cognieda.application.ports import ModelConfig, ProviderType
from cognieda.execution import Capability, ExecutorDispatcher, ExecutorRegistry
from cognieda.infrastructure.agent_tooling import AgentTooling

from .application import Application
from .workspace import Workspace


def bootstrap_application(workspace_path: Path) -> Application:
    workspace = Workspace.open(workspace_path)
    model_config = workspace.model_config

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
        agent_instruction=workspace.load_planner_agent_instruction(),
    )

    return Application(
        agent_factory=agent_factory,
        workspace=workspace,
        planner_agent=planner,
        dispatcher=dispatcher,
    )

