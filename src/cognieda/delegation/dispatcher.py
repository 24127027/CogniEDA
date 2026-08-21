from __future__ import annotations

from .contracts import ExecutorRequest, ExecutorResult
from .registry import CapabilityNotRegisteredError, ExecutorRegistry

class ExecutorDispatcher:
    """Thin typed dispatcher from a capability request to its registered provider."""

    def __init__(self, registry: ExecutorRegistry) -> None:
        self._registry = registry

    async def dispatch(self, request: ExecutorRequest) -> ExecutorResult:
        try:
            provider = self._registry.resolve(request.capability)
            result = await provider.run(request)
            if not isinstance(result, ExecutorResult):
                raise TypeError("Provider returned an incompatible result.")
            return result
        except CapabilityNotRegisteredError:
            raise
        except Exception as e:
            raise RuntimeError(f"Error during execution of capability {request.capability}: {e}") from e