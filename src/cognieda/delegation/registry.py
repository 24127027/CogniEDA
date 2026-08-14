from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .capabilities import Capability
from .contracts import Executor

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