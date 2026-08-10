from dataclasses import dataclass

from cognieda.application.ports import ExecutorDispatcherPort, PlannerStateMutationPort


@dataclass
class PlannerDeps:
    dispatcher: ExecutorDispatcherPort
    state_mutations: PlannerStateMutationPort
