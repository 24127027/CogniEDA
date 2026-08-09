# tools/builtin/terminal.py

from pydantic_ai import RunContext

from ..dependencies.protocols import HasTerminalPrinter

"""TODO: This is a temporary implementation of a terminal printer for testing purposes."""


async def print_to_terminal(
    ctx: RunContext[HasTerminalPrinter],
    message: str,
) -> str:
    """Print a message directly to the terminal for testing."""

    ctx.deps.terminal.print_pretty(message)

    return "Message printed to terminal."
