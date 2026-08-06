from pathlib import Path

from .application import Application
from .workspace import Workspace
from agents import Planner, ExecutorDispatcher, executor_registry

def bootstrap_application(workspace_path: Path) -> Application:
    workspace = Workspace.open(workspace_path)
    planner = Planner()
    executor_dispatcher = ExecutorDispatcher(registry=executor_registry)

    return Application(
        workspace=workspace,
        planner_agent=planner,
        dispatcher=executor_dispatcher
    )