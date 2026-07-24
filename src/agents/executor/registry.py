from __future__ import annotations

from collections.abc import Callable
from inspect import iscoroutinefunction

from .executor import DataExplorerAdapterProtocol

DataExplorerFactory = Callable[[], DataExplorerAdapterProtocol]
_SEPARATE_SPECIALIST_IDS = frozenset({"graph_mining", "hypothesis_testing"})


class DataExplorerRegistry:
    """One explicitly configured Data Explorer adapter per runtime."""

    def __init__(self) -> None:
        self._factories: dict[str, DataExplorerFactory] = {}
        self._instances: dict[str, DataExplorerAdapterProtocol] = {}

    def register_factory(
        self,
        executor_id: str,
        factory: DataExplorerFactory,
    ) -> None:
        """Register the runtime's one lazily constructed Data Explorer adapter."""

        executor_id = executor_id.strip()
        if not executor_id:
            raise ValueError("Data Explorer executor id cannot be empty.")
        if executor_id in _SEPARATE_SPECIALIST_IDS:
            raise ValueError(
                f"Executor id {executor_id!r} belongs to a separate specialist boundary."
            )
        if not callable(factory):
            raise TypeError("Data Explorer factory must be callable.")
        if self._factories:
            registered_id = next(iter(self._factories))
            raise ValueError(
                "Data Explorer registry already has an explicit registration: "
                f"{registered_id}"
            )

        self._factories[executor_id] = factory

    def get(self, executor_id: str) -> DataExplorerAdapterProtocol:
        if executor_id not in self._factories:
            raise KeyError(f"No Data Explorer registered for executor id: {executor_id}")

        if executor_id not in self._instances:
            adapter = self._factories[executor_id]()
            if not isinstance(adapter, DataExplorerAdapterProtocol) or not iscoroutinefunction(
                adapter.run
            ):
                raise TypeError(
                    "Data Explorer factory must return an adapter with an async run method."
                )
            self._instances[executor_id] = adapter

        return self._instances[executor_id]

    def list_executor_ids(self) -> tuple[str, ...]:
        return tuple(self._factories)
