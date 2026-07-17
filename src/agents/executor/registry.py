from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, create_model

from .capabilities import CAPABILITY_IDS, CapabilitySpec
from .executor import Executor

ExecutorFactory = Callable[[], Executor[Any]]


class ExecutorRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, ExecutorFactory] = {}
        self._instances: dict[str, Executor[Any]] = {}
        self._specs: dict[str, CapabilitySpec] = {}

    def register(
        self,
        capability: CapabilitySpec,
    ) -> Callable[[type[Executor[Any]]], type[Executor[Any]]]:
        def decorator(executor_type: type[Executor[Any]]) -> type[Executor[Any]]:
            self.register_factory(capability, cast(ExecutorFactory, executor_type))
            return executor_type

        return decorator

    def register_factory(
        self,
        capability: CapabilitySpec,
        factory: ExecutorFactory,
    ) -> None:
        """Register one lazily invoked executor factory for a capability."""
        if capability.id in self._factories:
            raise ValueError(f"Capability already registered: {capability.id}")

        self._specs[capability.id] = capability
        self._factories[capability.id] = factory

    def get(self, capability_id: str) -> Executor[Any]:
        if capability_id not in self._factories:
            raise KeyError(f"No executor registered for capability: {capability_id}")

        if capability_id not in self._instances:
            self._instances[capability_id] = self._factories[capability_id]()

        return self._instances[capability_id]

    def get_spec(self, capability_id: str) -> CapabilitySpec:
        if capability_id not in self._specs:
            raise KeyError(f"No capability registered: {capability_id}")

        return self._specs[capability_id]

    def list_specs(self) -> tuple[CapabilitySpec, ...]:
        return tuple(self._specs.values())


def render_capabilities(capabilities: tuple[CapabilitySpec, ...]) -> str:
    return "\n".join(
        f"- {capability.id}: {capability.description}" for capability in capabilities
    )


def build_capability_selection_model(
    capabilities: tuple[CapabilitySpec, ...],
) -> type[BaseModel]:
    capability_ids = tuple(capability.id for capability in capabilities)

    if not capability_ids:
        raise ValueError("At least one capability is required to build a selection model.")

    unknown_ids = tuple(
        capability_id for capability_id in capability_ids if capability_id not in CAPABILITY_IDS
    )
    if unknown_ids:
        raise ValueError(f"Unknown capability ids: {', '.join(unknown_ids)}")

    capability_type = Literal[capability_ids]

    return create_model(
        "CapabilitySelection",
        __config__=ConfigDict(extra="forbid"),
        capability=(
            capability_type,
            Field(description="Selected executor capability id."),
        ),
    )


def build_capability_selection_instructions(
    capabilities: tuple[CapabilitySpec, ...],
) -> str:
    if not capabilities:
        raise ValueError("At least one capability is required to build selection instructions.")

    return (
        "Choose exactly one executor capability for the task.\n"
        "Use only these capability ids:\n\n"
        f"{render_capabilities(capabilities)}\n\n"
        "Return the selected id in the `capability` field. Do not invent capability ids."
    )


executor_registry = ExecutorRegistry()

# Backward-compatible module-level name while the planner scaffold is migrated.
registry = executor_registry
