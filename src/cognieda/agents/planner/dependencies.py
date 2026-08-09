from dataclasses import dataclass

from cognieda.tools.dependencies.protocols import ExecutorDispatcherPort, TerminalPrinter


@dataclass
class PlannerDeps:
    terminal: TerminalPrinter
    dispatcher: ExecutorDispatcherPort
