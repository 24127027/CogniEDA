"""Injected context for DE graph nodes (dependencies + input payload)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from cognieda.schemas.artifacts import DataProfile


class DEInput(BaseModel):
    """Read-only dataset context injected into the DE workflow at invocation time."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    task_instruction: str
    dataset_path: str
    dataset_digest: str
    # Authoritative profile; None means this is a profiling request
    data_profile: DataProfile | None = None


class Context(BaseModel):
    """LangGraph context carrying DE model handle and the immutable DE input."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    de_model: object  # DataExplorerModel; typed as object to avoid circular import
    de_input: DEInput


__all__ = ("Context", "DEInput")
