from __future__ import annotations

import pandas as pd

from data.profiling import profile_dataframe
from schemas.enums import DataProfileMethod, LogicalDtype


def test_profile_dataframe_uses_semantic_logical_dtypes() -> None:
    dataframe = pd.DataFrame(
        {
            "numeric_col": [1.0, 2.5, 3.0],
            "bool_col": [True, False, True],
            "time_col": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
            "category_col": ["a", "b", "a"],
            "missing_col": [1.0, None, 3.0],
        }
    )

    profile = profile_dataframe(
        dataframe,
        dataset_path="data/test-profile.csv",
        dvc_hash="md5:test-profile-v1",
        method=DataProfileMethod.BASELINE_SUMMARY,
    )

    columns = {column.name: column for column in profile.schema_summary.columns}

    assert columns["numeric_col"].logical_dtype == LogicalDtype.NUMERIC
    assert columns["numeric_col"].numeric_summary is not None

    assert columns["bool_col"].logical_dtype == LogicalDtype.BOOLEAN
    assert columns["bool_col"].categorical_summary is not None

    assert columns["time_col"].logical_dtype == LogicalDtype.DATETIME
    assert columns["time_col"].categorical_summary is None
    assert "time_col" in profile.schema_summary.inferred_time_columns

    assert columns["category_col"].logical_dtype == LogicalDtype.CATEGORICAL
    assert columns["category_col"].categorical_summary is not None

    assert columns["missing_col"].observed_nullable is True
    assert profile.dataset_path == "data/test-profile.csv"
    assert profile.dvc_hash == "md5:test-profile-v1"
    assert profile.baseline_summary.numeric_column_count == 2
    assert profile.baseline_summary.categorical_column_count == 2
