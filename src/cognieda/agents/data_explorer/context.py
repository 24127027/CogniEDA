"""Injected context for DE graph nodes (dependencies + input payload)."""

from __future__ import annotations

import pandas as pd
from pydantic import BaseModel, ConfigDict, field_validator

from cognieda.schemas.artifacts import DataProfile


class DEInput(BaseModel):
    """Read-only dataset context injected into the DE workflow at invocation time.

    The ``dataframe`` field holds the in-memory dataset that the toolsets will
    operate on.  It is treated as immutable: the toolset factories always
    receive a deep copy so the original frame is never mutated by tool calls.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    task_instruction: str
    dataset_path: str
    dataset_digest: str
    # Authoritative profile; None means this is a profiling request
    data_profile: DataProfile | None = None
    # In-memory DataFrame.  None for unit-test / stub runs.
    dataframe: pd.DataFrame | None = None

    @field_validator("dataframe", mode="before")
    @classmethod
    def _copy_dataframe(cls, value: pd.DataFrame | None) -> pd.DataFrame | None:
        """Store a defensive copy of the caller's DataFrame."""
        if isinstance(value, pd.DataFrame):
            return value.copy(deep=True)
        return value


class Context(BaseModel):
    """LangGraph context carrying DE model handle and the immutable DE input."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    de_model: object  # DataExplorerModel; typed as object to avoid circular import
    de_input: DEInput


__all__ = ("Context", "DEInput")
