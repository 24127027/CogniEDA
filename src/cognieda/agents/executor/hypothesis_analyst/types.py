from __future__ import annotations

from pydantic import Field

from cognieda.schemas.artifacts import Discovery, Evidence, Hypothesis

from ..types import ExecutionResult


class HypothesisAnalystResult(ExecutionResult):
    """Role-native donor result; the specialist remains unregistered in S0."""

    hypothesis_draft: Hypothesis | None = None
    evidence_drafts: list[Evidence] = Field(default_factory=list)
    discovery_draft: Discovery | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    execution_details: list[str] = Field(default_factory=list)
    evaluation_outcome: str | None = None
    scientific_value: str | None = None
