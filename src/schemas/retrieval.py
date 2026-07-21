"""Typed contracts for bounded Discovery retrieval used during planning."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from schemas.common import CogniEDABaseModel
from schemas.enums import DiscoveryEpistemicStatus, DiscoveryLifecycleState


class RetrievalRequest(CogniEDABaseModel):
    """Bounded parameters for planning-only Discovery retrieval."""

    parent_task_id: UUID | None = None
    query_text: str | None = None
    max_results: int = Field(default=8, ge=1, le=32)
    candidate_pool_limit: int = Field(default=64, ge=1, le=256)


class RetrievalResultItem(BaseModel):
    """Internal metadata that explains one bounded Discovery candidate."""

    model_config = ConfigDict(extra="forbid")

    discovery_id: UUID
    claim_statement: str
    epistemic_status: DiscoveryEpistemicStatus
    lifecycle_state: DiscoveryLifecycleState
    relevance_score: float
    inclusion_reasons: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)


class RetrievalResult(BaseModel):
    """Planning candidates plus visible exclusions applied by the retrieval policy."""

    model_config = ConfigDict(extra="forbid")

    candidates: list[RetrievalResultItem] = Field(default_factory=list)
    exclusion_notes: list[str] = Field(default_factory=list)
