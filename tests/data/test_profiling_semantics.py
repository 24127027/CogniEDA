from __future__ import annotations

import json

import pandas as pd

from data.profiling import ProfilingOptions, profile_dataframe
from schemas import ContinuousColumnSummary, DiscreteColumnSummary, VariableType


def test_profile_dataframe_preserves_shape_order_dtype_and_missingness() -> None:
    dataframe = pd.DataFrame(
        {
            "amount": [1.0, None, 3.0],
            "active": [True, False, True],
            "segment": pd.Categorical(["premium", "standard", "premium"]),
        }
    )

    profile = profile_dataframe(dataframe)

    assert profile.row_count == 3
    assert profile.column_count == 3
    assert [column.name for column in profile.columns] == ["amount", "active", "segment"]
    assert [column.dtype for column in profile.columns] == ["float64", "bool", "category"]
    assert profile.columns[0].missing_count == 1
    assert profile.columns[0].distinct_count == 2


def test_numeric_non_boolean_is_continuous_with_finite_descriptive_summary() -> None:
    profile = profile_dataframe(pd.DataFrame({"amount": [1.0, 2.0, 3.0, 4.0]}))
    column = profile.columns[0]

    assert column.variable_type is VariableType.CONTINUOUS
    assert isinstance(column.summary, ContinuousColumnSummary)
    assert column.summary.min == 1.0
    assert column.summary.max == 4.0
    assert column.summary.mean == 2.5
    assert column.summary.median == 2.5
    assert column.summary.std is not None
    assert column.summary.p25 == 1.75
    assert column.summary.p75 == 3.25


def test_boolean_string_and_categorical_columns_are_discrete() -> None:
    dataframe = pd.DataFrame(
        {
            "active": [True, False, True],
            "name": ["a", "b", "a"],
            "segment": pd.Categorical(["x", "y", "x"]),
        }
    )

    profile = profile_dataframe(dataframe)

    assert all(column.variable_type is VariableType.DISCRETE for column in profile.columns)
    assert all(isinstance(column.summary, DiscreteColumnSummary) for column in profile.columns)


def test_low_cardinality_counts_are_complete_and_deterministically_ordered() -> None:
    profile = profile_dataframe(pd.DataFrame({"segment": ["b", "a", "b", "c"]}))
    summary = profile.columns[0].summary

    assert isinstance(summary, DiscreteColumnSummary)
    assert summary.top_values is None
    assert [(item.value, item.count) for item in summary.value_counts or ()] == [
        ("b", 2),
        ("a", 1),
        ("c", 1),
    ]


def test_high_cardinality_values_are_bounded_to_top_n() -> None:
    profile = profile_dataframe(
        pd.DataFrame({"code": ["d", "a", "b", "c", "d", "e"]}),
        options=ProfilingOptions(top_value_limit=3),
    )
    summary = profile.columns[0].summary

    assert isinstance(summary, DiscreteColumnSummary)
    assert summary.value_counts is None
    assert [(item.value, item.count) for item in summary.top_values or ()] == [
        ("d", 2),
        ("a", 1),
        ("b", 1),
    ]


def test_empty_dataset_retains_columns_and_json_safe_summaries() -> None:
    dataframe = pd.DataFrame(
        {
            "amount": pd.Series(dtype="float64"),
            "active": pd.Series(dtype="bool"),
        }
    )

    profile = profile_dataframe(dataframe)
    serialized = profile.model_dump(mode="json")

    assert profile.row_count == 0
    assert [column.name for column in profile.columns] == ["amount", "active"]
    assert isinstance(profile.columns[0].summary, ContinuousColumnSummary)
    assert profile.columns[0].summary.mean is None
    assert isinstance(profile.columns[1].summary, DiscreteColumnSummary)
    assert profile.columns[1].summary.value_counts == ()
    json.dumps(serialized, allow_nan=False)
