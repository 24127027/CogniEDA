"""Explicit deployment hook for loading the product-provided composition root."""

from __future__ import annotations

import importlib
import os
from collections.abc import Callable

from application.runtime import CogniEDARuntime, RuntimeConfigurationError

RuntimeFactory = Callable[[], CogniEDARuntime]


def load_runtime_from_environment() -> CogniEDARuntime:
    """Load an explicit ``module:factory`` hook; never synthesize missing adapters."""

    factory_path = os.environ.get("COGNIEDA_RUNTIME_FACTORY", "").strip()
    if not factory_path:
        raise RuntimeConfigurationError(
            "COGNIEDA_RUNTIME_FACTORY must name an explicit module:factory composition hook."
        )
    module_name, separator, attribute_name = factory_path.partition(":")
    if not separator or not module_name or not attribute_name:
        raise RuntimeConfigurationError(
            "COGNIEDA_RUNTIME_FACTORY must use the exact module:factory form."
        )
    module = importlib.import_module(module_name)
    factory = getattr(module, attribute_name, None)
    if not callable(factory):
        raise RuntimeConfigurationError(
            f"Configured runtime factory is not callable: {factory_path}."
        )
    runtime = factory()
    if not isinstance(runtime, CogniEDARuntime):
        raise RuntimeConfigurationError(
            "Configured runtime factory did not return CogniEDARuntime."
        )
    return runtime
