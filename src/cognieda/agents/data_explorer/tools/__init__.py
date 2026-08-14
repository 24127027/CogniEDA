"""Tools package for the Data Explorer.

Exports the three FunctionToolset factories and legacy helpers used by
the toolset implementations internally.
"""

from .analyze_dataset import (
    ColumnNotFoundError,
    DataToolError,
    InvalidAnalysisPlanError,
    InvalidToolResultError,
    normalize_json_value,
    tool_reference,
)
from .eda import eda_toolset
from .profiling import profiling_toolset
from .sandbox import SandboxSecurityError, SandboxTimeoutError, sandbox_toolset

__all__ = (
    # Toolset factories (primary API)
    "eda_toolset",
    "profiling_toolset",
    "sandbox_toolset",
    # Sandbox error types
    "SandboxSecurityError",
    "SandboxTimeoutError",
    # Legacy helpers (used internally by toolset implementations)
    "ColumnNotFoundError",
    "DataToolError",
    "InvalidAnalysisPlanError",
    "InvalidToolResultError",
    "normalize_json_value",
    "tool_reference",
)
