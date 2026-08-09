from dataclasses import dataclass

from cognieda.tools.dependencies.protocols import ExecutorDispatcherPort


@dataclass
class PlannerDeps:
    dispatcher: ExecutorDispatcherPort
