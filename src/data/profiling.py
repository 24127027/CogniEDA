"""Deterministic dataset profiling for the M1-A executable DataProfile."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import pandas as pd
from pandas.api import types as pd_types

from data.loaders import LoadedDataset, load_dataset
from data.validation import validate_profile_input_frame
from schemas.artifacts import DataProfile
from schemas.common import (
    ColumnProfile,
    ContinuousColumnSummary,
    DiscreteColumnSummary,
    DiscreteValueCount,
)
from schemas.enums import VariableType


@dataclass(frozen=True, slots=True)
class ProfilingOptions:
    """Deterministic bound for complete counts and high-cardinality top values."""

    top_value_limit: int = 5

    def __post_init__(self) -> None:
        if self.top_value_limit < 1:
            raise ValueError("top_value_limit must be at least 1.")


class DatasetProfiler:
    """Convert tabular data into one immutable, typed MVP DataProfile."""

    def __init__(self, options: ProfilingOptions | None = None) -> None:
        self._options = options or ProfilingOptions()

    def profile_loaded_dataset(self, loaded_dataset: LoadedDataset) -> DataProfile:
        """Profile an already-loaded dataset without embedding its location."""

        return self._build_profile(loaded_dataset.dataframe)

    def profile_dataframe(self, dataframe: pd.DataFrame) -> DataProfile:
        """Profile an in-memory dataframe without model or ontology participation."""

        return self._build_profile(dataframe)

    def profile_path(self, path: str) -> DataProfile:
        """Load and profile a supported dataset path."""

        return self.profile_loaded_dataset(load_dataset(path))

    def _build_profile(self, dataframe: pd.DataFrame) -> DataProfile:
        frame = validate_profile_input_frame(dataframe.copy())
        columns = tuple(self._profile_column(frame[column]) for column in frame.columns)
        return DataProfile(
            row_count=int(len(frame)),
            column_count=len(columns),
            columns=columns,
        )

    def _profile_column(self, series: pd.Series) -> ColumnProfile:
        variable_type = self._variable_type(series)
        summary: ContinuousColumnSummary | DiscreteColumnSummary
        if variable_type is VariableType.CONTINUOUS:
            summary = self._continuous_summary(series)
        else:
            summary = self._discrete_summary(series)

        return ColumnProfile(
            name=str(series.name),
            dtype=str(series.dtype),
            variable_type=variable_type,
            distinct_count=int(series.nunique(dropna=True)),
            missing_count=int(series.isna().sum()),
            summary=summary,
        )

    @staticmethod
    def _variable_type(series: pd.Series) -> VariableType:
        if pd_types.is_numeric_dtype(series) and not pd_types.is_bool_dtype(series):
            return VariableType.CONTINUOUS
        return VariableType.DISCRETE

    def _discrete_summary(self, series: pd.Series) -> DiscreteColumnSummary:
        counts = series.value_counts(dropna=True, sort=False)
        ordered_counts = sorted(
            (
                DiscreteValueCount(
                    value=self._json_scalar(value),
                    count=int(count),
                )
                for value, count in counts.items()
            ),
            key=lambda item: (
                -item.count,
                json.dumps(item.value, sort_keys=True, ensure_ascii=False),
            ),
        )

        if len(ordered_counts) <= self._options.top_value_limit:
            return DiscreteColumnSummary(value_counts=tuple(ordered_counts))
        return DiscreteColumnSummary(
            top_values=tuple(ordered_counts[: self._options.top_value_limit])
        )

    @classmethod
    def _json_scalar(cls, value: Any) -> str | int | float | bool:
        if hasattr(value, "item"):
            value = value.item()
        if isinstance(value, pd.Timestamp):
            return str(value.isoformat())
        if isinstance(value, bool):
            return value
        if isinstance(value, (str, int, float)):
            return value
        return str(value)

    @classmethod
    def _continuous_summary(cls, series: pd.Series) -> ContinuousColumnSummary:
        numeric = pd.to_numeric(series, errors="coerce").dropna()
        if numeric.empty:
            return ContinuousColumnSummary()
        return ContinuousColumnSummary(
            min=cls._as_float(numeric.min()),
            max=cls._as_float(numeric.max()),
            mean=cls._as_float(numeric.mean()),
            median=cls._as_float(numeric.median()),
            std=cls._as_float(numeric.std(ddof=0)),
            p25=cls._as_float(numeric.quantile(0.25)),
            p75=cls._as_float(numeric.quantile(0.75)),
        )

    @staticmethod
    def _as_float(value: Any) -> float | None:
        if value is None or pd.isna(value):
            return None
        return float(value)


def profile_dataframe(
    dataframe: pd.DataFrame,
    *,
    options: ProfilingOptions | None = None,
) -> DataProfile:
    """Convenience wrapper for deterministic in-memory profiling."""

    return DatasetProfiler(options=options).profile_dataframe(dataframe)


def profile_path(
    path: str,
    *,
    options: ProfilingOptions | None = None,
) -> DataProfile:
    """Convenience wrapper for loading and profiling one dataset path."""

    return DatasetProfiler(options=options).profile_path(path)
