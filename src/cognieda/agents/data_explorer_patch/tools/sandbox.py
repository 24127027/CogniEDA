from __future__ import annotations

import threading
from typing import Any
from uuid import uuid4

import numpy as np
import pandas as pd
from pydantic_ai import RunContext

from cognieda.agents.utilities import function_registry
from cognieda.schemas.artifacts import Evidence, EvidenceProvenance

from ..dependencies import DataExplorerDeps


sandbox = function_registry.FunctionRegistry()




SANDBOX_TIMEOUT = 15

_BLOCKED_MODULES = frozenset(
    {
        "os",
        "sys",
        "subprocess",
        "socket",
        "pathlib",
        "importlib",
        "shutil",
        "io",
        "builtins",
        "ctypes",
        "multiprocessing",
        "threading",
        "pickle",
        "shelve",
        "tempfile",
        "glob",
        "fnmatch",
    }
)


class SandboxTimeoutError(RuntimeError):
    pass


class SandboxSecurityError(RuntimeError):
    pass


def _safe_import(name: str, *args: Any, **kwargs: Any) -> Any:
    top_level = name.split(".")[0]

    if top_level in _BLOCKED_MODULES:
        raise SandboxSecurityError(
            f"Module '{name}' is blocked."
        )

    if top_level not in {
        "numpy",
        "pandas",
        "math",
        "statistics",
        "decimal",
        "fractions",
        "json",
    }:
        raise SandboxSecurityError(
            f"Module '{name}' is not allowed."
        )

    import importlib

    return importlib.import_module(name)


def _globals() -> dict[str, Any]:
    builtins = {
        "abs": abs,
        "all": all,
        "any": any,
        "bool": bool,
        "dict": dict,
        "enumerate": enumerate,
        "filter": filter,
        "float": float,
        "int": int,
        "isinstance": isinstance,
        "len": len,
        "list": list,
        "map": map,
        "max": max,
        "min": min,
        "print": print,
        "range": range,
        "repr": repr,
        "round": round,
        "set": set,
        "sorted": sorted,
        "str": str,
        "sum": sum,
        "tuple": tuple,
        "type": type,
        "zip": zip,
        "__import__": _safe_import,
    }

    return {
        "__builtins__": builtins,
        "pd": pd,
        "np": np,
    }


def _execute(
    code: str,
    namespace: dict[str, Any],
) -> None:
    exception: list[BaseException] = []

    def run() -> None:
        try:
            exec(
                compile(code, "<data_explorer_sandbox>", "exec"),
                namespace,
            )
        except BaseException as exc:
            exception.append(exc)

    thread = threading.Thread(
        target=run,
        daemon=True,
    )
    thread.start()
    thread.join(SANDBOX_TIMEOUT)

    if thread.is_alive():
        raise SandboxTimeoutError(
            f"Execution exceeded {SANDBOX_TIMEOUT} seconds."
        )

    if exception:
        raise exception[0]


def _serialize(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()

    if isinstance(value, pd.DataFrame):
        return value.to_dict(orient="records")

    if isinstance(value, pd.Series):
        return value.tolist()

    if isinstance(value, dict):
        return {
            str(key): _serialize(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]

    if value is None or isinstance(
        value,
        (str, int, float, bool),
    ):
        return value

    raise ValueError(
        f"Unsupported result type: {type(value).__name__}"
    )

@sandbox.register
def execute_code(
    ctx: RunContext[DataExplorerDeps],
    *,
    code: str,
) -> dict[str, Any]:
    """Execute custom pandas/numpy analysis against the active dataset.

    The code must assign its final result to ``result``.
    The available variables are ``df``, ``pd`` and ``np``.
    """

    namespace = _globals()
    namespace["df"] = ctx.deps.dataframe.copy(deep=True)

    try:
        _execute(code, namespace)

    except SandboxTimeoutError as exc:
        return {
            "error": "timeout",
            "detail": str(exc),
        }

    except SandboxSecurityError as exc:
        return {
            "error": "security",
            "detail": str(exc),
        }

    except Exception as exc:
        return {
            "error": "execution_error",
            "detail": str(exc),
        }

    if "result" not in namespace:
        return {
            "error": "missing_result",
            "detail": "Code must assign the final answer to 'result'.",
        }

    try:
        result = _serialize(namespace["result"])
    except Exception as exc:
        return {
            "error": "serialization_error",
            "detail": str(exc),
        }

    if not isinstance(result, dict):
        result = {"value": result}

    return {
        "output": result,
    }

__all__ = [
    "sandbox",
]