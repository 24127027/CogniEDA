from dataclasses import dataclass

from src.runtime.terminal import RichTerminalPrinter


@dataclass
class PlannerDeps:
    terminal: RichTerminalPrinter