"""Tools package for the Data Explorer.

Exports:
 - Pydantic AI FunctionToolset factories (for LLM-backed planning nodes)
 - Pure deterministic tool functions (for direct dispatch by execute node)
 - execute_analysis(): single-call dispatcher from DataAnalysisPlan to result
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from .analyze_dataset import (
    ColumnNotFoundError,
    DataToolError,
    InvalidAnalysisPlanError,
    InvalidToolResultError,
    normalize_json_value,
    tool_reference,
)
from .eda import eda_toolset
from .eda_tools import (
    run_column_summary,
    run_correlation,
    run_descriptive_statistics,
    run_group_summary,
    run_missingness,
    run_row_count,
    run_value_counts,
)
from .profiling import profiling_toolset
from .profiling_tools import compute_dataset_digest, profile_dataframe_to_dict
from .sandbox import SandboxSecurityError, SandboxTimeoutError, sandbox_toolset

if TYPE_CHECKING:
    from pydantic import JsonValue

    from cognieda.agents.data_explorer.contracts import DataAnalysisPlan, DataAnalysisOperation


def execute_analysis(
    plan: "DataAnalysisPlan",
    df: pd.DataFrame,
) -> "dict[str, JsonValue]":
    """Dispatch a validated DataAnalysisPlan to the matching deterministic tool.

    Raises DataToolError subclasses on column-not-found or invalid parameters.
    Raises InvalidToolResultError if the result is not JSON-serializable.
    """
    # Import here to avoid circular dependency at module load time.
    from cognieda.agents.data_explorer.contracts import DataAnalysisOperation

    op = plan.operation
    cols = list(plan.columns)

    if op is DataAnalysisOperation.ROW_COUNT:
        return run_row_count(df)

    if op is DataAnalysisOperation.COLUMN_SUMMARY:
        return run_column_summary(df, column=cols[0])

    if op is DataAnalysisOperation.MISSINGNESS:
        return run_missingness(df, columns=cols)

    if op is DataAnalysisOperation.VALUE_COUNTS:
        assert plan.top_k is not None
        return run_value_counts(df, column=cols[0], top_k=plan.top_k)

    if op is DataAnalysisOperation.DESCRIPTIVE_STATISTICS:
        return run_descriptive_statistics(df, column=cols[0])

    if op is DataAnalysisOperation.GROUP_SUMMARY:
        assert plan.max_groups is not None
        return run_group_summary(
            df,
            group_column=cols[0],
            value_column=cols[1],
            max_groups=plan.max_groups,
        )

    if op is DataAnalysisOperation.CORRELATION:
        assert plan.correlation_method is not None
        return run_correlation(df, columns=cols, method=plan.correlation_method.value)

    raise InvalidAnalysisPlanError(f"Unhandled operation: {op!r}")


__all__ = (
    # Toolset factories (LLM-backed planning node API)
    "eda_toolset",
    "profiling_toolset",
    "sandbox_toolset",
    # Sandbox error types
    "SandboxSecurityError",
    "SandboxTimeoutError",
    # Pure deterministic tool functions (direct dispatch API)
    "execute_analysis",
    "run_row_count",
    "run_column_summary",
    "run_missingness",
    "run_value_counts",
    "run_descriptive_statistics",
    "run_group_summary",
    "run_correlation",
    # Profiling tools
    "compute_dataset_digest",
    "profile_dataframe_to_dict",
    # Legacy helpers (used internally by toolset implementations)
    "ColumnNotFoundError",
    "DataToolError",
    "InvalidAnalysisPlanError",
    "InvalidToolResultError",
    "normalize_json_value",
    "tool_reference",
)
