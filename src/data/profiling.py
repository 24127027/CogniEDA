"""Baseline dataset profiling services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

import pandas as pd
from pandas.api import types as pd_types

from data.loaders import LoadedDataset, load_dataset
from data.validation import validate_profile_input_frame
from schemas.artifacts import DataProfile
from schemas.common import (
    BaselineSummary,
    CategoricalColumnSummary,
    ColumnSchemaSummary,
    NumericColumnSummary,
    QualityFlag,
    SchemaSummary,
    TopValueSummary,
)
from schemas.enums import DataProfileMethod, QualityFlagSeverity


@dataclass(frozen=True, slots=True)
class ProfilingOptions:
    """Deterministic configuration for baseline profiling behavior."""

    top_value_limit: int = 5
    high_missingness_threshold: float = 0.5


class DatasetProfiler:
    """Service for converting tabular datasets into typed baseline profiles."""

    def __init__(self, options: ProfilingOptions | None = None) -> None:
        self._options = options or ProfilingOptions()

    def profile_loaded_dataset(
        self,
        loaded_dataset: LoadedDataset,
        *,
        project_id: UUID,
        dataset_id: UUID,
        method: DataProfileMethod = DataProfileMethod.BASELINE_SUMMARY,
    ) -> DataProfile:
        """Profile a loaded dataset and return a typed `DataProfile`."""

        return self._build_profile(
            loaded_dataset.dataframe,
            project_id=project_id,
            dataset_id=dataset_id,
            method=method,
        )

    def profile_dataframe(
        self,
        dataframe: pd.DataFrame,
        *,
        project_id: UUID,
        dataset_id: UUID,
        method: DataProfileMethod = DataProfileMethod.BASELINE_SUMMARY,
    ) -> DataProfile:
        """Profile an in-memory dataframe."""

        return self._build_profile(
            dataframe,
            project_id=project_id,
            dataset_id=dataset_id,
            method=method,
        )

    def profile_path(
        self,
        path: str,
        *,
        project_id: UUID,
        dataset_id: UUID,
        method: DataProfileMethod = DataProfileMethod.BASELINE_SUMMARY,
    ) -> DataProfile:
        """Load and profile a dataset path in one step."""

        loaded_dataset = load_dataset(path)
        return self.profile_loaded_dataset(
            loaded_dataset,
            project_id=project_id,
            dataset_id=dataset_id,
            method=method,
        )

    def _build_profile(
        self,
        dataframe: pd.DataFrame,
        *,
        project_id: UUID,
        dataset_id: UUID,
        method: DataProfileMethod,
    ) -> DataProfile:
        dataframe = validate_profile_input_frame(dataframe.copy())
        row_count = int(len(dataframe))
        column_names = [str(column_name) for column_name in dataframe.columns.tolist()]
        column_summaries: list[ColumnSchemaSummary] = []
        inferred_time_columns: list[str] = []
        quality_flags: list[QualityFlag] = []
        missing_cell_count = int(dataframe.isna().sum().sum())
        duplicate_row_count = int(dataframe.duplicated().sum())
        numeric_column_count = 0
        categorical_column_count = 0
        columns_with_missing_values: list[str] = []

        if row_count == 0:
            quality_flags.append(
                QualityFlag(
                    code="empty_dataset",
                    severity=QualityFlagSeverity.WARNING,
                    message="Dataset has zero rows.",
                    column_name=None,
                )
            )

        for column_name in column_names:
            series = dataframe[column_name]
            column_summary = self._profile_column(series=series, row_count=row_count)
            column_summaries.append(column_summary)

            if column_summary.missing_count > 0:
                columns_with_missing_values.append(column_name)
            if column_summary.numeric_summary is not None:
                numeric_column_count += 1
            if column_summary.categorical_summary is not None:
                categorical_column_count += 1
            if pd_types.is_datetime64_any_dtype(series):
                inferred_time_columns.append(column_name)

            quality_flags.extend(self._column_quality_flags(column_summary))

        if duplicate_row_count > 0:
            quality_flags.append(
                QualityFlag(
                    code="duplicate_rows_detected",
                    severity=QualityFlagSeverity.WARNING,
                    message=f"Dataset contains {duplicate_row_count} duplicate rows.",
                    column_name=None,
                )
            )

        baseline_summary = BaselineSummary(
            column_names=column_names,
            missing_cell_count=missing_cell_count,
            missing_cell_ratio=self._safe_ratio(
                missing_cell_count,
                row_count * max(len(column_names), 1),
            ),
            duplicate_row_count=duplicate_row_count,
            duplicate_row_ratio=self._safe_ratio(duplicate_row_count, row_count),
            numeric_column_count=numeric_column_count,
            categorical_column_count=categorical_column_count,
            columns_with_missing_values=columns_with_missing_values,
            warning_codes=[quality_flag.code for quality_flag in quality_flags],
        )

        schema_summary = SchemaSummary(
            columns=column_summaries,
            column_order=column_names,
            detected_primary_key=self._detect_primary_key(dataframe),
            inferred_time_columns=inferred_time_columns,
        )

        return DataProfile(
            project_id=project_id,
            dataset_id=dataset_id,
            method=method,
            schema_summary=schema_summary,
            baseline_summary=baseline_summary,
            row_count=row_count,
            column_count=len(column_names),
            quality_flags=quality_flags,
        )

    def _profile_column(self, *, series: pd.Series, row_count: int) -> ColumnSchemaSummary:
        column_name = str(series.name)
        non_null_count = int(series.notna().sum())
        missing_count = int(series.isna().sum())
        distinct_count = int(series.nunique(dropna=True))
        missing_ratio = self._safe_ratio(missing_count, row_count)
        numeric_summary = (
            self._build_numeric_summary(series) if self._is_numeric_column(series) else None
        )
        categorical_summary = (
            self._build_categorical_summary(series)
            if self._is_categorical_like_column(series)
            else None
        )

        return ColumnSchemaSummary(
            name=column_name,
            inferred_dtype=str(series.dtype),
            nullable=missing_count > 0,
            non_null_count=non_null_count,
            distinct_count=distinct_count,
            missing_count=missing_count,
            missing_ratio=missing_ratio,
            numeric_summary=numeric_summary,
            categorical_summary=categorical_summary,
        )

    def _build_numeric_summary(self, series: pd.Series) -> NumericColumnSummary | None:
        numeric_series = pd.to_numeric(series, errors="coerce").dropna()
        if numeric_series.empty:
            return None

        return NumericColumnSummary(
            count=int(numeric_series.count()),
            mean=self._as_float(numeric_series.mean()),
            std=self._as_float(numeric_series.std(ddof=0)),
            min_value=self._as_float(numeric_series.min()),
            percentile_25=self._as_float(numeric_series.quantile(0.25)),
            median=self._as_float(numeric_series.median()),
            percentile_75=self._as_float(numeric_series.quantile(0.75)),
            max_value=self._as_float(numeric_series.max()),
        )

    def _build_categorical_summary(self, series: pd.Series) -> CategoricalColumnSummary | None:
        non_null_series = series.dropna()
        if non_null_series.empty:
            return CategoricalColumnSummary(unique_count=0, top_values=[])

        value_counts = non_null_series.astype(str).value_counts(dropna=False, sort=True)
        sorted_counts = value_counts.sort_index().sort_values(ascending=False, kind="stable")
        top_values = [
            TopValueSummary(
                value=str(value),
                count=int(count),
                ratio=self._safe_ratio(int(count), int(non_null_series.shape[0])),
            )
            for value, count in sorted_counts.head(self._options.top_value_limit).items()
        ]
        return CategoricalColumnSummary(
            unique_count=int(non_null_series.nunique()),
            top_values=top_values,
        )

    def _column_quality_flags(self, column_summary: ColumnSchemaSummary) -> list[QualityFlag]:
        flags: list[QualityFlag] = []

        if column_summary.non_null_count == 0:
            flags.append(
                QualityFlag(
                    code="column_all_missing",
                    severity=QualityFlagSeverity.WARNING,
                    message="Column contains only missing values.",
                    column_name=column_summary.name,
                )
            )
            return flags

        if column_summary.missing_ratio >= self._options.high_missingness_threshold:
            flags.append(
                QualityFlag(
                    code="high_missingness",
                    severity=QualityFlagSeverity.WARNING,
                    message=f"Column missingness ratio is {column_summary.missing_ratio:.2f}.",
                    column_name=column_summary.name,
                )
            )

        if column_summary.distinct_count == 1 and column_summary.non_null_count > 0:
            flags.append(
                QualityFlag(
                    code="constant_column",
                    severity=QualityFlagSeverity.INFO,
                    message="Column has a single non-null value.",
                    column_name=column_summary.name,
                )
            )

        return flags

    @staticmethod
    def _detect_primary_key(dataframe: pd.DataFrame) -> str | None:
        for column_name in dataframe.columns:
            series = dataframe[column_name]
            if series.notna().all() and series.is_unique:
                return str(column_name)
        return None

    @staticmethod
    def _is_numeric_column(series: pd.Series) -> bool:
        return pd_types.is_numeric_dtype(series) and not pd_types.is_bool_dtype(series)

    @staticmethod
    def _is_categorical_like_column(series: pd.Series) -> bool:
        return not DatasetProfiler._is_numeric_column(series)

    @staticmethod
    def _safe_ratio(numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0.0
        return float(numerator / denominator)

    @staticmethod
    def _as_float(value: Any) -> float | None:
        if value is None or pd.isna(value):
            return None
        return float(value)


def profile_dataframe(
    dataframe: pd.DataFrame,
    *,
    project_id: UUID,
    dataset_id: UUID,
    method: DataProfileMethod = DataProfileMethod.BASELINE_SUMMARY,
    options: ProfilingOptions | None = None,
) -> DataProfile:
    """Convenience wrapper for profiling an in-memory dataframe."""

    profiler = DatasetProfiler(options=options)
    return profiler.profile_dataframe(
        dataframe,
        project_id=project_id,
        dataset_id=dataset_id,
        method=method,
    )


def profile_path(
    path: str,
    *,
    project_id: UUID,
    dataset_id: UUID,
    method: DataProfileMethod = DataProfileMethod.BASELINE_SUMMARY,
    options: ProfilingOptions | None = None,
) -> DataProfile:
    """Convenience wrapper for loading and profiling a dataset path."""

    profiler = DatasetProfiler(options=options)
    return profiler.profile_path(path, project_id=project_id, dataset_id=dataset_id, method=method)
