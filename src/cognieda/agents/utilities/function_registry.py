from typing import Callable, Tuple, Any

class FunctionRegistry:
    def __init__(self) -> None:
        self._registry: list[Callable] = []

    def register(self, func: Callable) -> Callable:
        """Decorator to register a function."""
        if func not in self._registry:
            self._registry.append(func)
        return func  # Returns the original function unchanged

    def all(self) -> Tuple[Callable, ...]:
        """Returns a tuple of all registered functions."""
        return tuple(self._registry)