"""Pydantic AI FunctionToolset — Dataset Profiling & Schema Inspection.

All tools operate on a deep copy of the DataFrame supplied at construction.
No tool mutates the source frame.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from pydantic import JsonValue
from pydantic_ai import FunctionToolset, RunContext

from cognieda.agents.data_explorer.analysis.profiling import DatasetProfiler, ProfilingOptions
from cognieda.agents.data_explorer.analysis.validation import validate_profile_input_frame
from cognieda.agents.data_explorer.dependencies import DEDependencies
from cognieda.schemas.enums import VariableType


def profiling_toolset(df: pd.DataFrame) -> FunctionToolset:
    """Return a bound profiling toolset operating on an isolated DataFrame copy."""

    # Isolate the frame once for the entire toolset lifetime.
    _df = df.copy(deep=True)

    toolset: FunctionToolset = FunctionToolset()

    # ------------------------------------------------------------------
    # Tool: profile_dataset
    # ------------------------------------------------------------------

    @toolset.tool_plain
    def profile_dataset(top_value_limit: int = 5) -> dict[str, JsonValue]:
        """Produce a complete immutable typed profile of the bound dataset.

        Captures row count, column count, per-column dtype, distinct count,
        missing count, and continuous or discrete statistical summaries.
        Does NOT drop duplicate rows, all-null rows, or missing values.
        """
        options = ProfilingOptions(top_value_limit=max(1, top_value_limit))
        profile = DatasetProfiler(options=options).profile_dataframe(_df)
        return profile.model_dump(mode="json")

    # ------------------------------------------------------------------
    # Tool: inspect_schema
    # ------------------------------------------------------------------

    @toolset.tool_plain
    def inspect_schema() -> dict[str, JsonValue]:
        """Return a lightweight schema snapshot: column names, dtypes, and nullability.

        Cheaper than profile_dataset — no statistical computation is performed.
        """
        frame = validate_profile_input_frame(_df.copy(deep=True))
        columns: list[dict[str, JsonValue]] = []
        for col in frame.columns:
            series = frame[col]
            import pandas.api.types as pt

            logical = (
                VariableType.CONTINUOUS
                if (pt.is_numeric_dtype(series) and not pt.is_bool_dtype(series))
                else VariableType.DISCRETE
            )
            columns.append(
                {
                    "name": str(col),
                    "dtype": str(series.dtype),
                    "logical_type": logical.value,
                    "nullable": bool(series.isna().any()),
                }
            )
        return {
            "row_count": int(len(frame)),
            "column_count": len(columns),
            "columns": columns,
        }

    # ------------------------------------------------------------------
    # Tool: missingness_report
    # ------------------------------------------------------------------

    @toolset.tool  # context-aware: validates columns against live DataProfile
    def missingness_report(
        ctx: RunContext[DEDependencies],
        columns: list[str] | None = None,
    ) -> dict[str, JsonValue]:
        """Return per-column missing value counts and ratios.

        Args:
            columns: Optional subset of column names to examine. All columns
                     are reported when None.

        Uses the research DataProfile (when available) to validate that the
        requested column names actually exist before executing, providing a
        cleaner error message than a raw KeyError.
        """
        target_cols = columns if columns else list(_df.columns)

        # Context-aware validation: cross-check against DataProfile column names
        # when available to surface errors before touching the DataFrame.
        known_cols = ctx.deps.column_names if ctx.deps.column_names else list(_df.columns)
        invalid = [c for c in target_cols if c not in known_cols]
        if invalid:
            return {"error": f"Unknown columns (not in DataProfile or DataFrame): {invalid}"}

        missing = [c for c in target_cols if c not in _df.columns]
        if missing:
            return {"error": f"Columns not present in DataFrame: {missing}"}

        row_count = int(len(_df))
        per_column: list[dict[str, JsonValue]] = []
        for col in target_cols:
            mc = int(_df[col].isna().sum())
            per_column.append(
                {
                    "column": col,
                    "missing_count": mc,
                    "missing_ratio": round(mc / row_count, 6) if row_count else 0.0,
                }
            )

        complete_case_count = int(_df[target_cols].dropna().shape[0])
        return {
            "row_count": row_count,
            "complete_case_count": complete_case_count,
            "columns": per_column,
        }

    # ------------------------------------------------------------------
    # Tool: detect_duplicates
    # ------------------------------------------------------------------

    @toolset.tool_plain
    def detect_duplicates(subset_columns: list[str] | None = None) -> dict[str, JsonValue]:
        """Detect duplicate rows optionally restricted to a column subset.

        Args:
            subset_columns: Column names used for duplicate detection. All
                            columns are used when None.
        """
        subset = subset_columns if subset_columns else None
        dup_mask = _df.duplicated(subset=subset, keep=False)
        dup_count = int(dup_mask.sum())
        row_count = int(len(_df))

        return {
            "row_count": row_count,
            "duplicate_row_count": dup_count,
            "duplicate_ratio": round(dup_count / row_count, 6) if row_count else 0.0,
            "subset_columns_used": subset_columns,
        }

    return toolset


__all__ = ("profiling_toolset",)
