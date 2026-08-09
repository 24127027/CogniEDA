from __future__ import annotations

import os
from pathlib import Path

from cognieda.agents.data_explorer import DataExplorer
from cognieda.execution import Capability, ExecutorDispatcher, ExecutorRegistry
from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.dependencies import PlannerDeps

from .application import Application
from .terminal import RichTerminalPrinter
from .workspace import Workspace

NINE_ROUTER_BASE_URL = "http://localhost:20128/v1"


def bootstrap_application(workspace_path: Path) -> Application:
    workspace = Workspace.open(workspace_path)
    _configure_environment(workspace)

    registry = ExecutorRegistry()
    registry.register_provider(
        lambda: DataExplorer(),
        capabilities=(
            Capability.DATA_ANALYSIS,
            Capability.DATA_PROFILING,
            Capability.DATA_TRANSFORMATION,
        ),
    )
    dispatcher = ExecutorDispatcher(registry)
    terminal = RichTerminalPrinter()
    planner = Planner(
        deps=PlannerDeps(
            terminal=terminal,
            dispatcher=dispatcher,
        )
    )

    return Application(
        workspace=workspace,
        planner_agent=planner,
        dispatcher=dispatcher,
    )


def _configure_environment(workspace: Workspace) -> None:
    model_name = workspace.config.get("model.name")
    api_key = workspace.config.get("model.api_key", "local")

    if not model_name:
        raise ValueError("Missing [model].name in .cognieda/project.toml")

    os.environ["COGNIEDA_MODEL_NAME"] = str(model_name)
    os.environ["COGNIEDA_OPENAI_BASE_URL"] = NINE_ROUTER_BASE_URL
    os.environ["COGNIEDA_OPENAI_API_KEY"] = str(api_key)
