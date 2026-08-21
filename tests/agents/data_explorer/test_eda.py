from unittest.mock import MagicMock
from uuid import uuid4

import pandas as pd
import pytest

from cognieda.agents.data_explorer_patch.dependencies import DataExplorerDeps
from cognieda.agents.data_explorer_patch.tools.eda import (
    column_summary,
    descriptive_statistics,
    detect_outliers,
    distribution_histogram,
    group_summary,
    value_counts,
)


@pytest.fixture
def mock_ctx():
    df = pd.DataFrame({
        "num": [1, 2, 3, 4, 100],
        "cat": ["a", "b", "a", "a", "c"]
    })
    deps = DataExplorerDeps(dataframe=df, data_profile_id=uuid4())
    ctx = MagicMock()
    ctx.deps = deps
    return ctx

def test_column_summary(mock_ctx):
    res = column_summary(mock_ctx, column="num")
    assert res["column"] == "num"
    assert res["row_count"] == 5

def test_value_counts(mock_ctx):
    res = value_counts(mock_ctx, column="cat")
    assert len(res["values"]) == 3
    assert res["values"][0]["value"] == "a"
    assert res["values"][0]["count"] == 3

def test_descriptive_statistics(mock_ctx):
    res = descriptive_statistics(mock_ctx, column="num")
    assert res["finite_count"] == 5
    assert res["statistics"]["max"] == 100.0

def test_distribution_histogram(mock_ctx):
    res = distribution_histogram(mock_ctx, column="num", bins=2)
    assert res["bins"] == 2
    assert len(res["counts"]) == 2

def test_group_summary(mock_ctx):
    res = group_summary(mock_ctx, group_by="cat", value_column="num")
    assert len(res["groups"]) == 3
    for g in res["groups"]:
        if g["group"] == "a":
            assert g["finite_count"] == 3

def test_detect_outliers(mock_ctx):
    res = detect_outliers(mock_ctx, column="num", method="iqr")
    assert res["outlier_count"] == 1  # 100 is an outlier
