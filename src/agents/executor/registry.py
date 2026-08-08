from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from .capabilities import Capability
from .executor import Executor


ExecutorFactory = Callable[[], Executor[Any]]


class ExecutorRegistry:
    def __init__(self) -> None:
        self._providers: dict[Capability, ExecutorFactory] = {}
        self._instances: dict[ExecutorFactory, Executor[Any]] = {}

    def register(
        self,
        *capabilities: Capability,
    ) -> Callable[[type[Executor[Any]]], type[Executor[Any]]]:
        if not capabilities:
            raise ValueError("At least one capability must be registered.")

        def decorator(
            executor_type: type[Executor[Any]],
        ) -> type[Executor[Any]]:
            factory = cast(ExecutorFactory, executor_type)

            for capability in capabilities:
                if capability in self._providers:
                    raise ValueError(
                        f"Capability already registered: {capability}"
                    )

            for capability in capabilities:
                self._providers[capability] = factory

            return executor_type

        return decorator

    def get(self, capability: Capability) -> Executor[Any]:
        try:
            factory = self._providers[capability]
        except KeyError:
            raise KeyError(
                f"No executor registered for capability: {capability}"
            ) from None

        if factory not in self._instances:
            self._instances[factory] = factory()

        return self._instances[factory]


executor_registry = ExecutorRegistry()