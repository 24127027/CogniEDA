"""Optional dataframe validation helpers for dataset profiling."""

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


def validate_sample_profile_frame(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Example Pandera schema for the bundled sample profiling dataset."""

    schema = pa.DataFrameSchema(
        {
            "customer_id": pa.Column(int),
            "city": pa.Column(str, nullable=False),
            "plan": pa.Column(str, nullable=False),
            "country": pa.Column(str, nullable=False),
            "age": pa.Column(float, nullable=True),
            "monthly_spend": pa.Column(float, nullable=True),
            "notes": pa.Column(object, nullable=True),
        },
        strict=False,
        coerce=True,
    )
    return schema.validate(dataframe)
