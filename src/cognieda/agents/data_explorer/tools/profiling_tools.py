"""Deterministic profiling tool functions.

Pure Python functions for dataset profiling — no Pydantic AI dependencies.
The profiling_tools module wraps the DatasetProfiler from analysis/profiling.py
and returns a DataProfile object and a DataProfileCandidate with provenance.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

import pandas as pd

from cognieda.agents.data_explorer.analysis.profiling import DatasetProfiler, ProfilingOptions

__all__ = ("profile_dataframe_to_dict", "compute_dataset_digest")


def profile_dataframe_to_dict(
    df: pd.DataFrame,
    *,
    top_value_limit: int = 5,
):
    """Return an immutable DataProfile for the given DataFrame."""
    options = ProfilingOptions(top_value_limit=max(1, top_value_limit))
    return DatasetProfiler(options=options).profile_dataframe(df)


def compute_dataset_digest(path: str) -> str:
    """Return a sha256: prefixed hex digest of the file at path."""
    raw = Path(path).read_bytes()
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"
