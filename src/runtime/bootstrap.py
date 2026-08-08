import os
from pathlib import Path

from .application import Application
from .workspace import Workspace
from ..agents.planner.agent import Planner
from ..agents.planner.dependencies import PlannerDeps
from ..agents.executor.dispatcher import ExecutorDispatcher
from .terminal import RichTerminalPrinter
NINE_ROUTER_BASE_URL = "http://localhost:20128/v1"


def bootstrap_application(
    workspace_path: Path,
) -> Application:
    workspace = Workspace.open(workspace_path)
    _configure_environment(workspace)
    
    terminal = RichTerminalPrinter()
    dispatcher = None

    planner_deps = PlannerDeps(
        terminal=terminal,
    )

    planner = Planner(
        deps=planner_deps,
    )

    return Application(
        workspace=workspace,
        planner_agent=planner,
        dispatcher=dispatcher,
    )

def _configure_environment(
    workspace: Workspace,
) -> None:
    model_name = workspace.config.get("model.name")
    api_key = workspace.config.get("model.api_key", "local")

    if not model_name:
        raise ValueError(
            "Missing [model].name in "
            ".cognieda/project.toml"
        )

    os.environ["COGNIEDA_MODEL_NAME"] = str(model_name)
    os.environ["COGNIEDA_OPENAI_BASE_URL"] = (
        NINE_ROUTER_BASE_URL
    )
    os.environ["COGNIEDA_OPENAI_API_KEY"] = str(api_key)