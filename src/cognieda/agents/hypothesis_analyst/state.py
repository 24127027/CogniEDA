"""Internal state for the Hypothesis Analyst executor."""

from __future__ import annotations

from typing import TypedDict

from cognieda.delegation import ExecutionRequest
from cognieda.schemas.artifacts import Discovery, Evidence, Hypothesis

from .contracts import HypothesisAnalystResult


class HAState(TypedDict):
    request: ExecutionRequest
    hypothesis_draft: Hypothesis | None
    de_capability_requests: list[ExecutionRequest]
    collected_evidence: list[Evidence]
    evaluation_outcome: str | None
    scientific_value: str | None
    discovery_draft: Discovery | None
    execution_logs: list[str]
    final_result: HypothesisAnalystResult | None


State = HAState
