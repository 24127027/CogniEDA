from __future__ import annotations

from typing import Protocol

from cognieda.delegation import ExecutorRequest, ExecutorResult


class ExecutorDispatcherPort(Protocol):
    async def dispatch(self, request: ExecutorRequest) -> ExecutorResult: ...
