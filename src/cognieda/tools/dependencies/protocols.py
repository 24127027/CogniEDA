from __future__ import annotations

from typing import Protocol

from cognieda.agents.executor.types import ExecutionRequest, ExecutionResult


class ExecutorDispatcherPort(Protocol):
    async def dispatch(self, request: ExecutionRequest) -> ExecutionResult: ...


class HasExecutorDispatcher(Protocol):
    dispatcher: ExecutorDispatcherPort


class HasGraphRepository(Protocol):
    """Temporary dependency boundary for the existing graph tool scaffold."""


class HasDatasetRepository(Protocol):
    """Temporary dependency boundary for the existing dataset tool scaffold."""


class TerminalPrinter(Protocol):
    def print_pretty(self, message: str) -> None: ...


class HasTerminalPrinter(Protocol):
    terminal: TerminalPrinter
