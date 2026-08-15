"""Pydantic AI FunctionToolset — Descriptive & Exploratory Analysis (EDA).

Wraps the deterministic helpers from tools/analyze_dataset.py behind a
FunctionToolset so the Pydantic AI agent can call them by tool name.

All tools operate on the deep-copied DataFrame bound at toolset construction.
"""

from __future__ import annotations

import math
from typing import Literal

import numpy as np
import pandas as pd
from pydantic import JsonValue
from pydantic_ai import FunctionToolset

from cognieda.agents.data_explorer.tools.analyze_dataset import (
    ColumnNotFoundError,
    InvalidAnalysisPlanError,
    InvalidToolResultError,
    normalize_json_value,
    parse_string_list,
)


def eda_toolset(df: pd.DataFrame) -> FunctionToolset:
    """Return a bound EDA toolset operating on an isolated DataFrame copy."""

    _df = df.copy(deep=True)

    toolset: FunctionToolset = FunctionToolset()

    def _require_columns(*cols: str) -> None:
        missing = [c for c in cols if c not in _df.columns]
        if missing:
            raise ColumnNotFoundError(f"Column(s) not found: {missing}")

    def _numeric_finite(column: str) -> pd.Series:
        series = _df[column]
        if not pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series):
            raise InvalidAnalysisPlanError(f"Column '{column}' must be numeric.")
        numeric = pd.to_numeric(series, errors="coerce").astype("float64")
        return numeric[np.isfinite(numeric)]

    # ------------------------------------------------------------------
    # Tool: row_count
    # ------------------------------------------------------------------

    @toolset.tool_plain
    def row_count() -> dict[str, JsonValue]:
        """Return the total row count of the bound dataset."""
        return {"row_count": int(len(_df))}

    # ------------------------------------------------------------------
    # Tool: column_summary
    # ------------------------------------------------------------------

    @toolset.tool_plain
    def column_summary(column: str) -> dict[str, JsonValue]:
        """Return dtype, row count, missing count, and distinct count for one column.

        Args:
            column: Exact column name present in the dataset.
        """
        _require_columns(column)
        s = _df[column]
        return {
            "column": column,
            "dtype": str(s.dtype),
            "row_count": int(len(s)),
            "missing_count": int(s.isna().sum()),
            "non_missing_count": int(s.notna().sum()),
            "distinct_count": int(s.nunique(dropna=True)),
        }

    # ------------------------------------------------------------------
    # Tool: value_counts
    # ------------------------------------------------------------------

    @toolset.tool_plain
    def value_counts(column: str, top_k: int = 20) -> dict[str, JsonValue]:
        """Return frequency table for categorical or discrete series.

        Args:
            column: Exact column name to tabulate.
            top_k: Maximum number of top values to return (min 1, max 100).
        """
        _require_columns(column)
        top_k = max(1, min(top_k, 100))
        counts = _df[column].value_counts(dropna=False, sort=True).head(top_k)
        values: list[JsonValue] = []
        for val, cnt in counts.items():
            try:
                is_null = bool(pd.isna(val))
            except (TypeError, ValueError):
                is_null = False
            values.append({"value": None if is_null else normalize_json_value(val), "count": int(cnt)})
        return {"column": column, "top_k": top_k, "values": values}

    # ------------------------------------------------------------------
    # Tool: descriptive_statistics
    # ------------------------------------------------------------------

    @toolset.tool_plain
    def descriptive_statistics(column: str) -> dict[str, JsonValue]:
        """Return min, max, mean, median, std, p25, p75 for a numeric column.

        Args:
            column: Exact numeric column name.
        """
        _require_columns(column)
        finite = _numeric_finite(column)
        source = _df[column]
        n = int(len(finite))
        if n == 0:
            stats: dict[str, JsonValue] = {
                "min": None, "max": None, "mean": None,
                "median": None, "std": None, "p25": None, "p75": None,
            }
        else:
            stats = {
                "min": float(finite.min()),
                "max": float(finite.max()),
                "mean": float(finite.mean()),
                "median": float(finite.median()),
                "std": float(finite.std(ddof=1)) if n > 1 else 0.0,
                "p25": float(finite.quantile(0.25)),
                "p75": float(finite.quantile(0.75)),
            }
        return {
            "column": column,
            "finite_count": n,
            "missing_or_non_finite_count": int(len(source)) - n,
            "statistics": stats,
        }

    # ------------------------------------------------------------------
    # Tool: distribution_histogram
    # ------------------------------------------------------------------

    @toolset.tool_plain
    def distribution_histogram(column: str, bins: int = 10) -> dict[str, JsonValue]:
        """Return histogram bin edges, counts, and density for a numeric column.

        Args:
            column: Exact numeric column name.
            bins: Number of bins (1–50).
        """
        _require_columns(column)
        bins = max(1, min(bins, 50))
        finite = _numeric_finite(column)
        if finite.empty:
            return {"column": column, "bins": bins, "edges": [], "counts": [], "density": []}
        counts, edges = np.histogram(finite, bins=bins, density=False)
        total = int(counts.sum())
        density = [float(c) / total if total else 0.0 for c in counts]
        return {
            "column": column,
            "bins": bins,
            "edges": [round(float(e), 8) for e in edges],
            "counts": [int(c) for c in counts],
            "density": [round(d, 8) for d in density],
        }

    # ------------------------------------------------------------------
    # Tool: group_summary
    # ------------------------------------------------------------------

    @toolset.tool_plain
    def group_summary(
        group_by: str,
        value_column: str,
        max_groups: int = 50,
        aggregations: list[Literal["mean", "median", "sum", "std", "count"]] | None = None,
    ) -> dict[str, JsonValue]:
        """Aggregate a numeric column across groups of a categorical column.

        Args:
            group_by: Categorical column used for grouping.
            value_column: Numeric column to aggregate.
            max_groups: Reject if distinct group count exceeds this value.
            aggregations: Subset of ["mean", "median", "sum", "std", "count"].
        """
        _require_columns(group_by, value_column)
        aggs = aggregations or ["mean", "count"]
        _numeric_finite(value_column)

        records: list[dict[str, JsonValue]] = []
        grouped = _df.groupby(group_by, dropna=False, sort=False)[value_column]
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
            }
            if "count" in aggs:
                row["finite_count"] = int(len(finite))
            if "mean" in aggs:
                row["mean"] = float(finite.mean()) if len(finite) else None
            if "median" in aggs:
                row["median"] = float(finite.median()) if len(finite) else None
            if "sum" in aggs:
                row["sum"] = float(finite.sum()) if len(finite) else None
            if "std" in aggs:
                row["std"] = float(finite.std(ddof=1)) if len(finite) > 1 else (0.0 if len(finite) == 1 else None)
            records.append(row)

        records.sort(key=lambda r: repr(r["group"]))
        if len(records) > max_groups:
            raise InvalidToolResultError(
                f"group_summary produced {len(records)} groups; limit is {max_groups}."
            )
        return {
            "group_column": group_by,
            "value_column": value_column,
            "aggregations": aggs,
            "groups": normalize_json_value(records),
        }

    # ------------------------------------------------------------------
    # Tool: contingency_table
    # ------------------------------------------------------------------

    @toolset.tool_plain
    def contingency_table(
        row_column: str,
        col_column: str,
        normalize: Literal["all", "index", "columns"] | None = None,
    ) -> dict[str, JsonValue]:
        """Cross-tabulate two categorical columns.

        Args:
            row_column: Column to place on rows.
            col_column: Column to place on columns.
            normalize: Optional normalization axis — "all", "index", or "columns".
        """
        _require_columns(row_column, col_column)
        ct = pd.crosstab(
            _df[row_column],
            _df[col_column],
            margins=True,
            normalize=normalize if normalize else False,
        )
        rows: list[dict[str, JsonValue]] = []
        for idx, row in ct.iterrows():
            rows.append(
                {"index": str(idx), "values": {str(c): normalize_json_value(v) for c, v in row.items()}}
            )
        return {
            "row_column": row_column,
            "col_column": col_column,
            "normalize": normalize,
            "table": rows,
        }

    # ------------------------------------------------------------------
    # Tool: correlation_matrix
    # ------------------------------------------------------------------

    @toolset.tool_plain
    def correlation_matrix(
        columns: list[str] | str,
        method: Literal["pearson", "spearman", "kendall"] = "pearson",
    ) -> dict[str, JsonValue]:
        """Compute the pairwise correlation matrix for a set of numeric columns.

        Args:
            columns: List of 2 or more numeric column names.
            method: "pearson", "spearman", or "kendall".
        """
        if isinstance(columns, str):
            columns = parse_string_list(columns)
        if len(columns) < 2:
            raise InvalidAnalysisPlanError("correlation_matrix requires at least 2 columns.")
        _require_columns(*columns)
        for col in columns:
            _numeric_finite(col)

        mat = _df.loc[:, columns].corr(method=method)
        rows: list[JsonValue] = []
        for row_col in columns:
            values: list[JsonValue] = []
            for col in columns:
                val = float(mat.loc[row_col, col])
                values.append(val if math.isfinite(val) else None)
            rows.append({"column": row_col, "values": values})

        return {"columns": columns, "method": method, "matrix": rows}

    # ------------------------------------------------------------------
    # Tool: detect_outliers
    # ------------------------------------------------------------------

    @toolset.tool_plain
    def detect_outliers(
        column: str,
        method: Literal["iqr", "zscore"] = "iqr",
        threshold: float = 1.5,
    ) -> dict[str, JsonValue]:
        """Identify extreme values using IQR or Z-score method.

        Args:
            column: Exact numeric column name.
            method: "iqr" (Tukey fence) or "zscore" (standard score).
            threshold: IQR multiplier (default 1.5) or Z-score cutoff (e.g. 3.0).
        """
        _require_columns(column)
        finite = _numeric_finite(column)
        if finite.empty:
            return {"column": column, "method": method, "outlier_count": 0, "outlier_ratio": 0.0}

        if method == "iqr":
            q25, q75 = float(finite.quantile(0.25)), float(finite.quantile(0.75))
            iqr_val = q75 - q25
            lower = q25 - threshold * iqr_val
            upper = q75 + threshold * iqr_val
        else:
            mean = float(finite.mean())
            std = float(finite.std(ddof=1)) if len(finite) > 1 else 0.0
            lower = mean - threshold * std
            upper = mean + threshold * std

        mask = (finite < lower) | (finite > upper)
        outlier_count = int(mask.sum())
        return {
            "column": column,
            "method": method,
            "threshold": threshold,
            "lower_bound": round(lower, 8),
            "upper_bound": round(upper, 8),
            "outlier_count": outlier_count,
            "outlier_ratio": round(outlier_count / len(finite), 6) if len(finite) else 0.0,
        }

    return toolset


__all__ = ("eda_toolset",)
