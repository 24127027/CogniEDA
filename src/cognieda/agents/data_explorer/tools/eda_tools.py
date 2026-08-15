"""Deterministic EDA tool functions for the 7 Data Explorer operations.

Each function receives a DataFrame and operation-specific parameters and returns
a plain dict[str, JsonValue] payload matching the exact shapes tested in
test_m3a_execution.py.  No Pydantic AI dependencies.
"""

from __future__ import annotations

import math
from typing import Any, Literal

import numpy as np
import pandas as pd
from pydantic import JsonValue

from .analyze_dataset import (
    ColumnNotFoundError,
    InvalidAnalysisPlanError,
    InvalidToolResultError,
    normalize_json_value,
)

__all__ = (
    "run_row_count",
    "run_column_summary",
    "run_missingness",
    "run_value_counts",
    "run_descriptive_statistics",
    "run_group_summary",
    "run_correlation",
)


def _require_columns(df: pd.DataFrame, *cols: str) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ColumnNotFoundError(f"Column(s) not found in dataset: {missing}")


def _numeric_finite(df: pd.DataFrame, column: str) -> pd.Series:
    series = df[column]
    if not pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series):
        raise InvalidAnalysisPlanError(f"Column '{column}' must be numeric.")
    numeric = pd.to_numeric(series, errors="coerce").astype("float64")
    return numeric[np.isfinite(numeric)]


# ---------------------------------------------------------------------------
# ROW_COUNT
# ---------------------------------------------------------------------------


def run_row_count(df: pd.DataFrame) -> dict[str, JsonValue]:
    """Return the total row count of the dataset."""
    return {"row_count": int(len(df))}


# ---------------------------------------------------------------------------
# COLUMN_SUMMARY
# ---------------------------------------------------------------------------


def run_column_summary(df: pd.DataFrame, *, column: str) -> dict[str, JsonValue]:
    """Return dtype, row count, missing count, non_missing_count, and distinct count for one column."""
    _require_columns(df, column)
    s = df[column]
    return {
        "column": column,
        "dtype": str(s.dtype),
        "row_count": int(len(s)),
        "missing_count": int(s.isna().sum()),
        "non_missing_count": int(s.notna().sum()),
        "distinct_count": int(s.nunique(dropna=True)),
    }


# ---------------------------------------------------------------------------
# MISSINGNESS
# ---------------------------------------------------------------------------


def run_missingness(df: pd.DataFrame, *, columns: list[str]) -> dict[str, JsonValue]:
    """Return per-column missing counts and missing_rate for the requested columns."""
    _require_columns(df, *columns)
    row_count = int(len(df))
    per_column: list[dict[str, JsonValue]] = []
    for col in columns:
        mc = int(df[col].isna().sum())
        per_column.append(
            {
                "column": col,
                "missing_count": mc,
                "missing_rate": round(mc / row_count, 6) if row_count else 0.0,
            }
        )
    return {"row_count": row_count, "columns": per_column}


# ---------------------------------------------------------------------------
# VALUE_COUNTS
# ---------------------------------------------------------------------------


def run_value_counts(
    df: pd.DataFrame,
    *,
    column: str,
    top_k: int,
) -> dict[str, JsonValue]:
    """Return frequency table for a discrete/categorical column."""
    _require_columns(df, column)
    top_k = max(1, min(top_k, 50))
    counts = df[column].value_counts(dropna=False, sort=True).head(top_k)
    values: list[JsonValue] = []
    for val, cnt in counts.items():
        try:
            is_null = bool(pd.isna(val))
        except (TypeError, ValueError):
            is_null = False
        values.append({"value": None if is_null else normalize_json_value(val), "count": int(cnt)})
    return {"column": column, "top_k": top_k, "values": values}


# ---------------------------------------------------------------------------
# DESCRIPTIVE_STATISTICS
# ---------------------------------------------------------------------------


def run_descriptive_statistics(df: pd.DataFrame, *, column: str) -> dict[str, JsonValue]:
    """Return min, max, mean, median, standard_deviation, p25, p75 for a numeric column."""
    _require_columns(df, column)
    finite = _numeric_finite(df, column)
    source = df[column]
    n = int(len(finite))
    if n == 0:
        stats: dict[str, JsonValue] = {
            "min": None, "max": None, "mean": None,
            "median": None, "standard_deviation": None, "p25": None, "p75": None,
        }
    else:
        stats = {
            "min": float(finite.min()),
            "max": float(finite.max()),
            "mean": float(finite.mean()),
            "median": float(finite.median()),
            "standard_deviation": float(finite.std(ddof=1)) if n > 1 else 0.0,
            "p25": float(finite.quantile(0.25)),
            "p75": float(finite.quantile(0.75)),
        }
    return {
        "column": column,
        "finite_count": n,
        "missing_or_non_finite_count": int(len(source)) - n,
        "statistics": stats,
    }


# ---------------------------------------------------------------------------
# GROUP_SUMMARY
# ---------------------------------------------------------------------------


def run_group_summary(
    df: pd.DataFrame,
    *,
    group_column: str,
    value_column: str,
    max_groups: int,
) -> dict[str, JsonValue]:
    """Aggregate a numeric value_column across groups of a categorical group_column."""
    _require_columns(df, group_column, value_column)
    _numeric_finite(df, value_column)

    records: list[dict[str, JsonValue]] = []
    grouped = df.groupby(group_column, dropna=False, sort=False)[value_column]
    for grp_val, vals in grouped:
        numeric = pd.to_numeric(vals, errors="coerce").astype("float64")
        finite = numeric[np.isfinite(numeric)]
        try:
            is_null = bool(pd.isna(grp_val))
        except (TypeError, ValueError):
            is_null = False
        row: dict[str, JsonValue] = {
            "group": None if is_null else normalize_json_value(grp_val),
            "row_count": int(len(vals)),
            "finite_count": int(len(finite)),
            "mean": float(finite.mean()) if len(finite) else None,
            "sum": float(finite.sum()) if len(finite) else None,
        }
        records.append(row)

    records.sort(key=lambda r: repr(r["group"]))
    if len(records) > max_groups:
        raise InvalidToolResultError(
            f"group_summary produced {len(records)} groups; limit is {max_groups}."
        )
    return {
        "group_column": group_column,
        "value_column": value_column,
        "groups": normalize_json_value(records),
    }


# ---------------------------------------------------------------------------
# CORRELATION
# ---------------------------------------------------------------------------


def run_correlation(
    df: pd.DataFrame,
    *,
    columns: list[str],
    method: Literal["pearson", "spearman"] = "pearson",
) -> dict[str, JsonValue]:
    """Compute a pairwise correlation matrix for the listed numeric columns."""
    if len(columns) < 2:
        raise InvalidAnalysisPlanError("correlation requires at least 2 columns.")
    _require_columns(df, *columns)
    for col in columns:
        _numeric_finite(df, col)

    mat = df.loc[:, columns].corr(method=method)
    rows: list[JsonValue] = []
    for row_col in columns:
        values: list[JsonValue] = []
        for col in columns:
            val = float(mat.loc[row_col, col])
            values.append(val if math.isfinite(val) else None)
        rows.append({"column": row_col, "values": values})

    return {"columns": columns, "method": method, "matrix": rows}
