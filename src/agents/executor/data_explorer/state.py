"""Internal state for the Data Explorer executor."""

from __future__ import annotations

from typing import Any, TypedDict

from schemas.artifacts import DataProfile, Evidence

from ..types import ExecutionRequest, ExecutionResult


class DEState(TypedDict):
    request: ExecutionRequest
    raw_data_results: Any
    evidence_draft: Evidence | None
    data_profile_draft: DataProfile | None
    execution_logs: list[str]
    retry_count: int
    final_result: ExecutionResult | None


State = DEState