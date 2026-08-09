"""Deterministic allowlisted analytical tools for the M3-A Evidence path."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
from pydantic import JsonValue

from cognieda.execution import DataAnalysisOperation, DataAnalysisPlan

TOOL_VERSION = "v1"


class DataToolError(ValueError):
    """Expected deterministic tool rejection with a stable failure code."""

    code = "tool_execution_error"


class ColumnNotFoundError(DataToolError):
    code = "column_not_found"


class InvalidAnalysisPlanError(DataToolError):
    code = "invalid_analysis_plan"


class InvalidToolResultError(DataToolError):
    code = "invalid_result"


def tool_reference(operation: DataAnalysisOperation) -> str:
    return f"cognieda.data_explorer.{operation.value}:{TOOL_VERSION}"


def normalize_json_value(value: Any) -> JsonValue:
    """Normalize supported scalar containers and reject opaque runtime objects."""

    if value is None or isinstance(value, (str, bool, int)):
        return value
    if value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, np.generic):
        return normalize_json_value(value.item())
    if isinstance(value, float):
        if not math.isfinite(value):
            raise InvalidToolResultError("Tool output contains a non-finite float.")
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Mapping):
        normalized: dict[str, JsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise InvalidToolResultError("Tool output requires string object keys.")
            normalized[key] = normalize_json_value(item)
        return normalized
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [normalize_json_value(item) for item in value]
    raise InvalidToolResultError(
        f"Tool output contains unsupported value type {type(value).__name__}."
    )


def _validate_columns(dataframe: pd.DataFrame, plan: DataAnalysisPlan) -> None:
    missing = [column for column in plan.columns if column not in dataframe.columns]
    if missing:
        raise ColumnNotFoundError(
            "Analysis requires exact existing column names; missing: " + ", ".join(missing)
        )


def _finite_numeric_series(dataframe: pd.DataFrame, column: str) -> pd.Series:
    series = dataframe[column]
    if not pd.api.types.is_numeric_dtype(series.dtype) or pd.api.types.is_bool_dtype(
        series.dtype
    ):
        raise InvalidAnalysisPlanError(f"Column {column!r} must be numeric.")
    numeric = pd.to_numeric(series, errors="coerce").astype("float64")
    return numeric[np.isfinite(numeric)]


def _row_count(dataframe: pd.DataFrame) -> dict[str, JsonValue]:
    return {"row_count": int(len(dataframe))}


def _column_summary(
    dataframe: pd.DataFrame, plan: DataAnalysisPlan
) -> dict[str, JsonValue]:
    column = plan.columns[0]
    series = dataframe[column]
    return {
        "column": column,
        "dtype": str(series.dtype),
        "row_count": int(len(series)),
        "non_missing_count": int(series.notna().sum()),
        "missing_count": int(series.isna().sum()),
        "distinct_count": int(series.nunique(dropna=True)),
    }


def _missingness(dataframe: pd.DataFrame, plan: DataAnalysisPlan) -> dict[str, JsonValue]:
    row_count = int(len(dataframe))
    columns: list[JsonValue] = []
    for column in plan.columns:
        missing_count = int(dataframe[column].isna().sum())
        columns.append(
            {
                "column": column,
                "missing_count": missing_count,
                "missing_rate": (missing_count / row_count if row_count else 0.0),
            }
        )
    return {"row_count": row_count, "columns": columns}


def _value_counts(dataframe: pd.DataFrame, plan: DataAnalysisPlan) -> dict[str, JsonValue]:
    column = plan.columns[0]
    assert plan.top_k is not None
    counts = dataframe[column].value_counts(dropna=False, sort=True).head(plan.top_k)
    values: list[JsonValue] = []
    for value, count in counts.items():
        normalized_value: JsonValue
        try:
            is_missing = bool(pd.isna(value))
        except (TypeError, ValueError):
            is_missing = False
        normalized_value = None if is_missing else normalize_json_value(value)
        values.append({"value": normalized_value, "count": int(count)})
    return {"column": column, "top_k": plan.top_k, "values": values}


def _descriptive_statistics(
    dataframe: pd.DataFrame, plan: DataAnalysisPlan
) -> dict[str, JsonValue]:
    column = plan.columns[0]
    source = dataframe[column]
    finite = _finite_numeric_series(dataframe, column)
    count = int(len(finite))
    if count == 0:
        statistics: dict[str, JsonValue] = {
            "min": None,
            "max": None,
            "mean": None,
            "median": None,
            "standard_deviation": None,
            "p25": None,
            "p75": None,
        }
    else:
        standard_deviation = float(finite.std(ddof=1)) if count > 1 else 0.0
        statistics = {
            "min": float(finite.min()),
            "max": float(finite.max()),
            "mean": float(finite.mean()),
            "median": float(finite.median()),
            "standard_deviation": standard_deviation,
            "p25": float(finite.quantile(0.25)),
            "p75": float(finite.quantile(0.75)),
        }
    return {
        "column": column,
        "finite_count": count,
        "missing_or_non_finite_count": int(len(source) - count),
        "statistics": statistics,
    }


def _group_summary(dataframe: pd.DataFrame, plan: DataAnalysisPlan) -> dict[str, JsonValue]:
    group_column, value_column = plan.columns
    assert plan.max_groups is not None
    _finite_numeric_series(dataframe, value_column)
    records: list[dict[str, JsonValue]] = []
    grouped = dataframe.groupby(group_column, dropna=False, sort=False)[value_column]
    for group_value, values in grouped:
        numeric = pd.to_numeric(values, errors="coerce").astype("float64")
        finite = numeric[np.isfinite(numeric)]
        try:
            is_missing = bool(pd.isna(group_value))
        except (TypeError, ValueError):
            is_missing = False
        records.append(
            {
                "group": None if is_missing else normalize_json_value(group_value),
                "row_count": int(len(values)),
                "finite_count": int(len(finite)),
                "mean": float(finite.mean()) if len(finite) else None,
                "sum": float(finite.sum()) if len(finite) else None,
            }
        )
    records.sort(key=lambda item: repr(item["group"]))
    if len(records) > plan.max_groups:
        raise InvalidToolResultError(
            f"group_summary produced {len(records)} groups; limit is {plan.max_groups}."
        )
    return {
        "group_column": group_column,
        "value_column": value_column,
        "groups": normalize_json_value(records),
    }


def _correlation(dataframe: pd.DataFrame, plan: DataAnalysisPlan) -> dict[str, JsonValue]:
    assert plan.correlation_method is not None
    for column in plan.columns:
        _finite_numeric_series(dataframe, column)
    matrix = dataframe.loc[:, list(plan.columns)].corr(method=plan.correlation_method.value)
    rows: list[JsonValue] = []
    for row_column in plan.columns:
        values: list[JsonValue] = []
        for column in plan.columns:
            value = float(matrix.loc[row_column, column])
            values.append(value if math.isfinite(value) else None)
        rows.append({"column": row_column, "values": values})
    return {
        "columns": list(plan.columns),
        "method": plan.correlation_method.value,
        "matrix": rows,
    }


def execute_analysis(
    dataframe: pd.DataFrame,
    plan: DataAnalysisPlan,
) -> dict[str, JsonValue]:
    """Execute exactly one validated plan without mutating the supplied DataFrame."""

    _validate_columns(dataframe, plan)
    operations = {
        DataAnalysisOperation.ROW_COUNT: lambda: _row_count(dataframe),
        DataAnalysisOperation.COLUMN_SUMMARY: lambda: _column_summary(dataframe, plan),
        DataAnalysisOperation.MISSINGNESS: lambda: _missingness(dataframe, plan),
        DataAnalysisOperation.VALUE_COUNTS: lambda: _value_counts(dataframe, plan),
        DataAnalysisOperation.DESCRIPTIVE_STATISTICS: lambda: _descriptive_statistics(
            dataframe, plan
        ),
        DataAnalysisOperation.GROUP_SUMMARY: lambda: _group_summary(dataframe, plan),
        DataAnalysisOperation.CORRELATION: lambda: _correlation(dataframe, plan),
    }
    result = operations[plan.operation]()
    normalized = normalize_json_value(result)
    if not isinstance(normalized, dict) or not normalized:
        raise InvalidToolResultError("A deterministic analysis must return a non-empty object.")
    return normalized
