from __future__ import annotations

from typing import Any, Literal, cast
from uuid import uuid4

import numpy as np
import pandas as pd
from pydantic_ai import RunContext

from cognieda.agents.utilities import function_registry
from cognieda.schemas.artifacts import Evidence, EvidenceProvenance

from ..dependencies import DataExplorerDeps

from cognieda.agents.utilities import function_registry



@eda.register
def submit_evidence(
    ctx: RunContext[DataExplorerDeps],
    content: dict[str, Any],
    artifact_refs: list[str],
) -> Evidence:
    """Submit your final analytical findings. Use this tool when you have fully answered the request."""
    return Evidence(
        # TODO: Dọn cái này sau (Match PlannerWorkOutcome mock)
        data_profile_id=ctx.deps.data_profile_id or uuid4(),
        content=content,
        artifact_refs=tuple(artifact_refs),
        provenance=EvidenceProvenance(
            producer_role="data_explorer",
            work_reference="eda",
            dataset_reference="active_dataframe",
            data_profile_id=ctx.deps.data_profile_id or uuid4(),
        ),
    )


def _column(df: pd.DataFrame, name: str) -> pd.Series:
    if name not in df.columns:
        raise ValueError(f"Column not found: {name}")
    return df[name]


def _numeric(df: pd.DataFrame, name: str) -> pd.Series:
    series = _column(df, name)

    if not pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series):
        raise ValueError(f"Column '{name}' must be numeric.")

    return pd.to_numeric(series, errors="coerce").astype("float64")

@eda.register
def column_summary(
    ctx: RunContext[DataExplorerDeps],
    *,
    column: str,
) -> dict[str, Any]:
    """Summarize basic properties of one column."""
    df = ctx.deps.dataframe
    series = _column(df, column)

    return {
        "column": column,
        "dtype": str(series.dtype),
        "row_count": len(series),
        "missing_count": int(series.isna().sum()),
        "distinct_count": int(series.nunique(dropna=True)),
    }

@eda.register
def value_counts(
    ctx: RunContext[DataExplorerDeps],
    *,
    column: str,
    top_k: int = 20,
) -> dict[str, Any]:
    """Return the most frequent values of a column."""
    df = ctx.deps.dataframe
    series = _column(df, column)

    top_k = max(1, min(top_k, 100))
    counts = series.value_counts(dropna=False).head(top_k)

    values = []
    for value, count in counts.items():
        if pd.isna(cast(Any, value)):
            val_out = None
        elif isinstance(value, np.generic):
            val_out = value.item()
        else:
            val_out = value

        values.append(
            {
                "value": val_out,
                "count": int(count),
            }
        )

    return {
        "column": column,
        "top_k": top_k,
        "values": values,
    }

@eda.register
def descriptive_statistics(
    ctx: RunContext[DataExplorerDeps],
    *,
    column: str,
) -> dict[str, Any]:
    """Return basic descriptive statistics for a numeric column."""
    df = ctx.deps.dataframe
    series = _numeric(df, column)
    valid_values = series[np.isfinite(series)]

    if valid_values.empty:
        statistics = {
            "min": None,
            "max": None,
            "mean": None,
            "median": None,
            "std": None,
            "p25": None,
            "p75": None,
        }
    else:
        statistics = {
            "min": float(valid_values.min()),
            "max": float(valid_values.max()),
            "mean": float(valid_values.mean()),
            "median": float(valid_values.median()),
            "std": float(valid_values.std(ddof=1)) if len(valid_values) > 1 else None,
            "p25": float(valid_values.quantile(0.25)),
            "p75": float(valid_values.quantile(0.75)),
        }

    return {
        "column": column,
        "finite_count": len(valid_values),
        "missing_or_non_finite_count": len(series) - len(valid_values),
        "statistics": statistics,
    }

@eda.register
def distribution_histogram(
    ctx: RunContext[DataExplorerDeps],
    *,
    column: str,
    bins: int = 10,
) -> dict[str, Any]:
    """Return histogram counts and bin edges for a numeric column."""
    df = ctx.deps.dataframe
    series = _numeric(df, column)
    valid_values = series[np.isfinite(series)]

    bins = max(1, min(bins, 50))

    if valid_values.empty:
        return {
            "column": column,
            "bins": bins,
            "edges": [],
            "counts": [],
        }

    counts, edges = np.histogram(valid_values.to_numpy(), bins=bins)

    return {
        "column": column,
        "bins": bins,
        "edges": [float(e) for e in edges],
        "counts": [int(c) for c in counts],
    }

@eda.register
def group_summary(
    ctx: RunContext[DataExplorerDeps],
    *,
    group_by: str,
    value_column: str,
    aggregations: list[
        Literal["mean", "median", "sum", "std", "count"]
    ] | None = None,
) -> dict[str, Any]:
    """Aggregate a numeric column by another column."""
    df = ctx.deps.dataframe

    _column(df, group_by)
    _numeric(df, value_column)

    aggregations = aggregations or ["mean", "count"]
    allowed = {"mean", "median", "sum", "std", "count"}

    if not set(aggregations).issubset(allowed):
        raise ValueError(
            f"Unsupported aggregation. Choose from {sorted(allowed)}."
        )

    grouped = df.groupby(group_by, dropna=False, sort=False)[value_column]
    groups = []

    for group_key, series in grouped:
        numeric_series = pd.to_numeric(series, errors="coerce").astype("float64")
        valid_values = numeric_series[np.isfinite(numeric_series)]

        if pd.isna(cast(Any, group_key)):
            grp_out = None
        elif isinstance(group_key, np.generic):
            grp_out = group_key.item()
        else:
            grp_out = group_key

        result: dict[str, Any] = {
            "group": grp_out,
            "row_count": len(series),
        }

        if "count" in aggregations:
            result["finite_count"] = len(valid_values)

        if "mean" in aggregations:
            result["mean"] = (
                float(valid_values.mean()) if len(valid_values) else None
            )

        if "median" in aggregations:
            result["median"] = (
                float(valid_values.median()) if len(valid_values) else None
            )

        if "sum" in aggregations:
            result["sum"] = (
                float(valid_values.sum()) if len(valid_values) else None
            )

        if "std" in aggregations:
            result["std"] = (
                float(valid_values.std(ddof=1))
                if len(valid_values) > 1
                else None
            )

        groups.append(result)

    return {
        "group_column": group_by,
        "value_column": value_column,
        "aggregations": aggregations,
        "groups": groups,
    }

@eda.register
def detect_outliers(
    ctx: RunContext[DataExplorerDeps],
    *,
    column: str,
    method: Literal["iqr", "zscore"] = "iqr",
    threshold: float = 1.5,
) -> dict[str, Any]:
    """Detect outliers in a numeric column."""
    df = ctx.deps.dataframe
    series = _numeric(df, column)
    valid_values = series[np.isfinite(series)]

    if threshold <= 0:
        raise ValueError("threshold must be greater than zero.")

    if method not in {"iqr", "zscore"}:
        raise ValueError("method must be 'iqr' or 'zscore'.")

    if valid_values.empty:
        return {
            "column": column,
            "method": method,
            "threshold": threshold,
            "outlier_count": 0,
            "outlier_ratio": 0.0,
        }

    if method == "iqr":
        q25 = float(valid_values.quantile(0.25))
        q75 = float(valid_values.quantile(0.75))
        iqr = q75 - q25

        lower = q25 - threshold * iqr
        upper = q75 + threshold * iqr
    else:
        mean = float(valid_values.mean())
        std = float(valid_values.std(ddof=1)) if len(valid_values) > 1 else 0.0

        lower = mean - threshold * std
        upper = mean + threshold * std  # Sửa bug: thay '-' bằng '+'

    outliers = (valid_values < lower) | (valid_values > upper)
    count = int(outliers.sum())

    return {
        "column": column,
        "method": method,
        "threshold": threshold,
        "lower_bound": lower,
        "upper_bound": upper,
        "outlier_count": count,
        "outlier_ratio": float(count / len(valid_values)),
    }

__all__ = [
    "eda"
]