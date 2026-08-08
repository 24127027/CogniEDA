from typing import Protocol
from src.agents.executor.dispatcher import ExecutorDispatcher

"""
    This module defines protocols for dependencies that can be used in tools
    Agents can declare it own dependencies by using these protocols
    Agent's dependencies are required to contain protocols that are used by the tools it uses,
      so that the agent can be properly initialized with the required dependencies.

"""

class HasExecutorDispatcher(Protocol):
    dispatcher: ExecutorDispatcher
class HasGraphRepository(Protocol):
    """
        Dummy dependencies protocols for testing purposes.
    """
    ...

class HasDatasetRepository(Protocol):
    """
        Dummy dependencies protocols for testing purposes.
    """
    ...

"""TODO: REMOVE: This is a temporary implementation of a terminal printer for testing purposes."""
class TerminalPrinter(Protocol):
    def print_pretty(self, message: str) -> None:
        ...


class HasTerminalPrinter(Protocol):
    terminal: TerminalPrinter