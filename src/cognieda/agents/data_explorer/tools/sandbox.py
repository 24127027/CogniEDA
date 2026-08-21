"""Pydantic AI FunctionToolset — Sandboxed Python/Pandas Code Executor.

Executes LLM-generated code against an isolated DataFrame copy in a
restricted environment.  This is the escape hatch when no builtin tool
covers the requested operation.

Safety invariants
-----------------
- Operates on ``df.copy(deep=True)`` — source data is never mutated.
- Restricted builtins: os, sys, subprocess, socket, pathlib, importlib
  and any module accessing the filesystem or network are blocked.
- Execution timeout: 15 seconds (configurable via ``SANDBOX_TIMEOUT``).
- The only pre-bound names in the execution namespace are:
    ``df``  — a deep copy of the active DataFrame
    ``pd``  — pandas
    ``np``  — numpy
- The executed code must assign ``result`` to a JSON-serializable dict.
"""

from __future__ import annotations

import threading
from typing import Any

import numpy as np
import pandas as pd
from pydantic_ai import FunctionToolset

from cognieda.agents.data_explorer.tools.analyze_dataset import normalize_json_value
from cognieda.agents.data_explorer.tools.analyze_dataset import parse_string_list

SANDBOX_TIMEOUT = 15  # seconds


class SandboxTimeoutError(RuntimeError):
    """Raised when sandboxed code exceeds the execution time limit."""


class SandboxSecurityError(RuntimeError):
    """Raised when sandboxed code attempts a blocked operation."""


_BLOCKED_MODULES = frozenset(
    {
        "os",
        "sys",
        "subprocess",
        "socket",
        "pathlib",
        "importlib",
        "importlib.util",
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


def _build_restricted_globals() -> dict[str, Any]:
    """Return a minimal global namespace that blocks dangerous builtins."""

    def _safe_import(name: str, *args: Any, **kwargs: Any) -> Any:
        top = name.split(".")[0]
        if top in _BLOCKED_MODULES:
            raise SandboxSecurityError(
                f"Module '{name}' is blocked in the Data Explorer sandbox."
            )
        # Allow numpy and pandas and stdlib math/statistics
        allowed = {"numpy", "np", "pandas", "pd", "math", "statistics", "decimal", "fractions", "json"}
        if top not in allowed:
            raise SandboxSecurityError(
                f"Module '{name}' is not in the sandbox allowlist."
            )
        import importlib

        return importlib.import_module(name)

    safe_builtins = {
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
        "print": print,  # harmless for diagnostics
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
    return {"__builtins__": safe_builtins, "pd": pd, "np": np}


def _run_with_timeout(
    code: str,
    namespace: dict[str, Any],
    timeout: int,
) -> None:
    """Execute ``code`` in ``namespace`` with a hard timeout using a thread."""

    exc_holder: list[BaseException] = []

    def _target() -> None:
        try:
            exec(compile(code, "<de_sandbox>", "exec"), namespace)  # noqa: S102
        except Exception as exc:  # noqa: BLE001
            exc_holder.append(exc)

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        raise SandboxTimeoutError(
            f"Sandboxed code exceeded the {timeout}-second time limit."
        )
    if exc_holder:
        raise exc_holder[0]


def sandbox_toolset(df: pd.DataFrame) -> FunctionToolset:
    """Return a sandbox toolset bound to an isolated DataFrame copy."""

    _df = df.copy(deep=True)

    toolset: FunctionToolset = FunctionToolset()

    @toolset.tool_plain
    def execute_code(
        code: str,
        target_columns: list[str] | str | None = None,
    ) -> dict[str, Any]:
        """Execute custom Python/Pandas code against the bound DataFrame.

        The code must assign the final answer to a variable named ``result``.
        ``result`` must be a dict (or a scalar that can be wrapped in one).

        The DataFrame is pre-bound as ``df``. Only ``pd`` and ``np`` are
        available as external libraries.

        Args:
            code: Python source code to execute. Must set ``result``.
            target_columns: Column names the code intends to access. Used for
                            provenance capture; does not restrict execution.
        """
        if isinstance(target_columns, str):
            target_columns = parse_string_list(target_columns)
            
        namespace = _build_restricted_globals()
        namespace["df"] = _df.copy(deep=True)

        try:
            _run_with_timeout(code, namespace, SANDBOX_TIMEOUT)
        except SandboxTimeoutError as exc:
            return {"error": "timeout", "detail": str(exc)}
        except SandboxSecurityError as exc:
            return {"error": "security", "detail": str(exc)}
        except Exception as exc:  # noqa: BLE001
            return {"error": "execution_error", "detail": str(exc)}

        raw_result = namespace.get("result")
        if raw_result is None:
            return {
                "error": "missing_result",
                "detail": "Code did not assign a 'result' variable.",
            }

        if not isinstance(raw_result, dict):
            raw_result = {"value": raw_result}

        try:
            payload = normalize_json_value(raw_result)
        except Exception as exc:  # noqa: BLE001
            return {"error": "serialization_error", "detail": str(exc)}

        # Provenance: collect which columns were accessed
        accessed = [c for c in (target_columns or []) if c in _df.columns]
        values_observed: dict[str, Any] = {}
        for col in accessed:
            if col in _df.columns:
                s = _df[col].dropna()
                if len(s):
                    try:
                        values_observed[col] = {"sample_n": int(len(s))}
                    except Exception:  # noqa: BLE001
                        pass

        return {
            "output": payload,
            "variables_accessed": accessed,
            "values_observed": values_observed,
        }

    return toolset


__all__ = ("SandboxSecurityError", "SandboxTimeoutError", "sandbox_toolset")
