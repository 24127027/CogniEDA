from rich.console import Console
from rich.panel import Panel

"""TODO: This is a temporary implementation of a terminal printer for testing purposes. 
It should be removed once tools are ensured to work correctly"""

class RichTerminalPrinter:
    def __init__(self) -> None:
        self._console = Console()

    def print_pretty(self, message: str) -> None:
        self._console.print(
            Panel(
                message,
                title="Planner",
                border_style="cyan",
            )
        )