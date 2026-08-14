from __future__ import annotations

from .contracts import ExecutionRequest, ExecutionResult
from .registry import CapabilityNotRegisteredError, ExecutorRegistry


class ExecutorProviderError(RuntimeError):
    def __init__(self, request: ExecutionRequest, cause: Exception) -> None:
        self.capability = request.capability
        self.task_id = request.input.task.task_id
        super().__init__(
            f"Provider for {request.capability} failed for Task {self.task_id}: {cause}"
        )


class ExecutorDispatcher:
    """Thin typed dispatcher from a capability request to its registered provider."""

    def __init__(self, registry: ExecutorRegistry) -> None:
        self._registry = registry

    async def dispatch(self, request: ExecutionRequest) -> ExecutionResult:
        try:
            provider = self._registry.resolve(request.capability)
            result = await provider.run(request)
            if not isinstance(result, ExecutionResult):
                raise TypeError("Provider returned an incompatible result.")
            return result
        except CapabilityNotRegisteredError:
            raise
        except Exception as exc:
            if isinstance(exc, ExecutorProviderError):
                raise
            raise ExecutorProviderError(request, exc) from exc
