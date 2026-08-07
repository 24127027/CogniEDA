import os
from pathlib import Path

from .application import Application
from .workspace import Workspace
from ..agents.planner.agent import Planner


NINE_ROUTER_BASE_URL = "http://localhost:20128/v1"


def bootstrap_application(
    workspace_path: Path,
) -> Application:
    workspace = Workspace.open(workspace_path)

    _configure_environment(workspace)

    # Add these when the MVP Planner is ready.
    planner = Planner()
    executor_dispatcher = None

    return Application(
        workspace=workspace,
        planner_agent=planner,
        dispatcher=executor_dispatcher,
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