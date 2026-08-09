from __future__ import annotations

import pandas as pd

from cognieda.schemas.artifacts import DataProfile

from ..analysis import DatasetProfiler, ProfilingOptions


def profile_dataset(
    dataframe: pd.DataFrame,
    *,
    options: ProfilingOptions | None = None,
) -> DataProfile:
    """Profile the active dataset exactly as supplied, without transformation."""

    return DatasetProfiler(options=options).profile_dataframe(dataframe)
