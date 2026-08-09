"""Structural validation for the Data Explorer profiling computation."""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
from pandera import Check


def validate_profile_input_frame(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Validate minimal structural assumptions before profiling a dataframe."""

    schema = pa.DataFrameSchema(
        columns={},
        checks=[
            Check(
                lambda df: len(df.columns) > 0,
                error="DataFrame must contain at least one column.",
            ),
            Check(
                lambda df: not df.columns.duplicated().any(),
                error="DataFrame column names must be unique.",
            ),
        ],
        strict=False,
        coerce=False,
    )
    return schema.validate(dataframe)
