"""Internal state for the Data Explorer executor."""

from __future__ import annotations

from typing import Any, TypedDict

from cognieda.schemas.artifacts import DataProfile

from ..types import ExecutionRequest
from .types import DataExplorerObservation, DataExplorerResult


class DEState(TypedDict):
    request: ExecutionRequest
    raw_data_results: Any
    observation: DataExplorerObservation | None
    data_profile_draft: DataProfile | None
    execution_logs: list[str]
    retry_count: int
    final_result: DataExplorerResult | None


State = DEState
