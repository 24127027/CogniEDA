from dataclasses import dataclass

from cognieda.application.ports import ExecutorDispatcherPort


@dataclass
class PlannerDeps:
    dispatcher: ExecutorDispatcherPort
