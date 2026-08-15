from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Union

from .capabilities import Capability
from .contracts import Executor

# A factory is any zero-arg callable returning an Executor, or an Executor class.
ExecutorFactory = Callable[[], Executor]

class CapabilityNotRegisteredError(LookupError):
    pass

@dataclass(slots=True)
class _Registration:
    factory: ExecutorFactory
    instance: Executor | None = None

class ExecutorRegistry:
    """Capability -> Executor registry with lazy executor creation."""

    def __init__(self) -> None:
        self._registrations: dict[Capability, _Registration] = {}

    def register(self, factory: ExecutorFactory) -> None:
        if not callable(factory):
            raise TypeError("factory must be callable.")

        # Construct once for validation and metadata extraction.
        executor = factory()

        if not isinstance(executor, Executor):
            raise TypeError("Factory returned an incompatible executor.")

        capabilities = getattr(executor, "CAPABILITIES", None)
        if capabilities is None:
            raise TypeError(
                f"{type(executor).__name__} must define CAPABILITIES."
            )
        
        capabilities = tuple(capabilities)

        if len(set(capabilities)) != len(capabilities):
            raise ValueError(
                f"{type(executor).__name__} declares duplicate capabilities."
            )

        registration = _Registration(factory=factory)

        for capability in capabilities:
            if not isinstance(capability, Capability):
                raise TypeError(
                    f"{type(executor).__name__} declares an invalid capability: {capability!r}"
                )

            if capability in self._registrations:
                raise ValueError(
                    f"Capability already registered: {capability}"
                )

            self._registrations[capability] = registration

    def register_provider(
        self,
        provider: Union[ExecutorFactory, type],
        *,
        capabilities: tuple[Capability, ...],
    ) -> None:
        """Register a class or factory callable for the given explicit capabilities.

        All capabilities share the same lazy instance (one factory call for all).

        Args:
            provider: An Executor subclass, or any zero-arg callable that returns
                      an Executor.  When a class is passed it is used as the factory.
            capabilities: Non-empty tuple of Capability values to map to this provider.

        Raises:
            ValueError: If capabilities is empty or a capability is already registered.
            TypeError: If the factory returns an incompatible object.
        """
        if not capabilities:
            raise ValueError(
                "At least one capability must be specified when registering a provider."
            )

        # Normalise: if it's a class, wrap in a zero-arg lambda so we get fresh
        # instances but share the same registration object (lazy singleton per registry).
        factory: ExecutorFactory = provider if not isinstance(provider, type) else provider

        # Validate all capabilities first before mutating state.
        for capability in capabilities:
            if not isinstance(capability, Capability):
                raise TypeError(
                    f"Invalid capability: {capability!r}. Must be a Capability instance."
                )
            if capability in self._registrations:
                raise ValueError(f"Capability already registered: {capability}")

        # One shared _Registration for all capabilities → same instance on resolve.
        registration = _Registration(factory=factory)
        for capability in capabilities:
            self._registrations[capability] = registration

    def resolve(self, capability: Capability) -> Executor:
        if not isinstance(capability, Capability):
            raise TypeError("capability must be a Capability.")

        try:
            registration = self._registrations[capability]
        except KeyError:
            raise CapabilityNotRegisteredError(
                f"No executor registered for capability: {capability}"
            ) from None

        if registration.instance is None:
            executor = registration.factory()

            if not isinstance(executor, Executor):
                raise TypeError(
                    "Factory returned an incompatible executor."
                )

            registration.instance = executor

        return registration.instance

    def reload(self, capability: Capability) -> None:
        """Recreate the executor on next resolve()."""
        try:
            self._registrations[capability].instance = None
        except KeyError:
            raise CapabilityNotRegisteredError(
                f"No executor registered for capability: {capability}"
            ) from None

    def reload_all(self) -> None:
        """Recreate all executors on next resolve()."""
        for registration in self._registrations.values():
            registration.instance = None

    def list_capabilities(self) -> tuple[Capability, ...]:
        return tuple(self._registrations)