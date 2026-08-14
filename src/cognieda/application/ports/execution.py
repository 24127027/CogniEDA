from __future__ import annotations

from typing import Protocol

from cognieda.delegation import ExecutionRequest, ExecutionResult


class ExecutorDispatcherPort(Protocol):
    async def dispatch(self, request: ExecutionRequest) -> ExecutionResult: ...
