from __future__ import annotations

from collections.abc import Callable, Iterable

from .capabilities import Capability
from .contracts import ExecutorProvider

ProviderFactory = Callable[[], ExecutorProvider]


class CapabilityNotRegisteredError(LookupError):
    pass


class ExecutorRegistry:
    """Explicit Capability -> ProviderFactory registry with lazy provider reuse."""

    def __init__(self) -> None:
        self._providers: dict[Capability, ProviderFactory] = {}
        self._instances: dict[ProviderFactory, ExecutorProvider] = {}

    def register_provider(
        self,
        provider_factory: ProviderFactory,
        *,
        capabilities: Iterable[Capability],
    ) -> None:
        registered = tuple(capabilities)
        if not registered:
            raise ValueError("At least one capability must be registered.")
        if not callable(provider_factory):
            raise TypeError("provider_factory must be callable.")
        if any(not isinstance(capability, Capability) for capability in registered):
            raise TypeError("Registered capabilities must be Capability values.")
        if len(set(registered)) != len(registered):
            raise ValueError("A registration cannot contain duplicate capabilities.")

        duplicate = next(
            (capability for capability in registered if capability in self._providers),
            None,
        )
        if duplicate is not None:
            raise ValueError(f"Capability already registered: {duplicate}")

        for capability in registered:
            self._providers[capability] = provider_factory

    def resolve(self, capability: Capability) -> ExecutorProvider:
        if not isinstance(capability, Capability):
            raise TypeError("Resolved capability must be a Capability value.")

        try:
            factory = self._providers[capability]
        except KeyError:
            raise CapabilityNotRegisteredError(
                f"No provider registered for capability: {capability}"
            ) from None

        if factory not in self._instances:
            provider = factory()
            if not isinstance(provider, ExecutorProvider):
                raise TypeError("Provider factory returned an incompatible provider.")
            self._instances[factory] = provider
        return self._instances[factory]

    def list_capabilities(self) -> tuple[Capability, ...]:
        return tuple(self._providers)
