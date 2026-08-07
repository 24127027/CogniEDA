from pathlib import Path
import os

from .application import Application
from .workspace import Workspace
from ..agents import Planner, ExecutorDispatcher, executor_registry

def bootstrap_application(workspace_path: Path) -> Application:
    workspace = Workspace.open(workspace_path)

    _configure_environment(workspace)

    planner = Planner()
    executor_dispatcher = ExecutorDispatcher(registry=executor_registry)

    return Application(
        workspace=workspace,
        planner_agent=planner,
        dispatcher=executor_dispatcher
    )

def _configure_environment(workspace: Workspace):
    os.environ["COGNIEDA_OPENAI_API_KEY"] = "COGNIEDA_OPENAI_API_KEY"  # Replace with actual logic to retrieve the API key
    os.environ["COGNIEDA_OPENAI_BASE_URL"] = "COGNIEDA_OPENAI_BASE_URL"  # Replace with actual logic to retrieve the base URL
    os.environ["COGNIEDA_OPENAI_MODEL_NAME"] = "COGNIEDA_OPENAI_MODEL_NAME"  # Replace with actual logic to retrieve the model name