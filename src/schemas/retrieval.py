"""Retrieval request and result contracts."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from schemas.common import CogniEDABaseModel
from schemas.enums import DiscoveryEpistemicStatus, DiscoveryLifecycleState


class RetrievalRequest(CogniEDABaseModel):
    """Typed parameters for bounded Discovery retrieval."""

    objective_id: UUID
    active_data_profile_id: UUID | None = None
    session_frame_id: UUID | None = None
    parent_task_id: UUID | None = None
    query_text: str | None = None
    max_results: int = Field(default=8, ge=1, le=32)
    candidate_pool_limit: int = Field(default=64, ge=1, le=256)


class RetrievalResultItem(BaseModel):
    """Retrieval metadata for one Discovery candidate."""

    model_config = ConfigDict(extra="forbid")

    discovery_id: UUID
    claim_statement: str
    epistemic_status: DiscoveryEpistemicStatus
    lifecycle_state: DiscoveryLifecycleState
    relevance_score: float
    structural_relations_used: list[str] = Field(default_factory=list)
    inclusion_reasons: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    is_pinned: bool = False
    eligible_for_motivation: bool = True


class RetrievalResult(BaseModel):
    """Separated result distinguishing motivation-eligible from contextual Discoveries."""

    model_config = ConfigDict(extra="forbid")

    motivation_candidates: list[RetrievalResultItem] = Field(default_factory=list)
    other_relevant_discoveries: list[RetrievalResultItem] = Field(default_factory=list)
    exclusion_notes: list[str] = Field(default_factory=list)
