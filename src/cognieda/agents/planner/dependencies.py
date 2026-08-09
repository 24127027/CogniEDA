from dataclasses import dataclass

from cognieda.application.ports import ExecutorDispatcherPort, PlannerResearchStatePort


@dataclass
class PlannerDeps:
    dispatcher: ExecutorDispatcherPort
    research_state: PlannerResearchStatePort
