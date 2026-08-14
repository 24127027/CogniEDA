from dataclasses import dataclass

from cognieda.application.ports import ExecutorDispatcherPort


@dataclass(frozen=True)
class PlannerDeps:
    """Model-hidden dependencies reserved for future semantic Planner tools."""

    dispatcher: ExecutorDispatcherPort
