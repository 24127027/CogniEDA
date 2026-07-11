from __future__ import annotations

from .registry import ExecutorRegistry
from .types import ExecutionRequest, ExecutionResult


class ExecutorDispatcher:
    def __init__(self, registry: ExecutorRegistry) -> None:
        self._registry = registry

    async def dispatch(self, request: ExecutionRequest) -> ExecutionResult:
        executor = self._registry.get(request.capability)

        return await executor.run(
            input=request.input,
            context=request.context,
        )
