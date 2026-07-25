"""Canonical SessionFrame research schema."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import Field

from schemas.common import (
    AssumptionContextSummary,
    CogniEDABaseModel,
    DataProfileContextSummary,
    DeadEndSummary,
    DiscoveryContextSummary,
    EvidenceContextSummary,
    HypothesisContextSummary,
    InvalidationRule,
    NonEmptyStr,
    StaleContextMarker,
    TaskContextSummary,
    ToolResultCacheSummary,
    UserDecisionContextSummary,
    utc_now,
)
from schemas.research.lifecycle import SessionFrameStatus


class SessionFrame(CogniEDABaseModel):
    """Concrete active-context frame for session continuity and handoff."""

    session_frame_id: UUID = Field(default_factory=uuid4)
    frame_topic: NonEmptyStr
    frame_status: SessionFrameStatus = SessionFrameStatus.ACTIVE
    objective_snapshot: NonEmptyStr
    frame_outcome: str | None = None
    objective_summary: str | None = None
    branch_key: str | None = None
    checkpoint_label: str | None = None
    parent_session_frame_id: UUID | None = None
    handoff_summary: str | None = None
    data_profile_summaries: list[DataProfileContextSummary] = Field(default_factory=list)
    active_data_profile_refs: list[UUID] = Field(default_factory=list)
    active_tasks: list[TaskContextSummary] = Field(default_factory=list)
    active_task_refs: list[UUID] = Field(default_factory=list)
    active_assumptions: list[AssumptionContextSummary] = Field(default_factory=list)
    active_assumption_refs: list[UUID] = Field(default_factory=list)
    active_hypotheses: list[HypothesisContextSummary] = Field(default_factory=list)
    active_hypothesis_refs: list[UUID] = Field(default_factory=list)
    relevant_discoveries: list[DiscoveryContextSummary] = Field(default_factory=list)
    relevant_discovery_refs: list[UUID] = Field(default_factory=list)
    supporting_evidence: list[EvidenceContextSummary] = Field(default_factory=list)
    supporting_evidence_refs: list[UUID] = Field(default_factory=list)
    recent_user_decisions: list[UserDecisionContextSummary] = Field(default_factory=list)
    recent_user_decision_refs: list[UUID] = Field(default_factory=list)
    pending_tasks: list[NonEmptyStr] = Field(default_factory=list)
    pending_proposals: list[NonEmptyStr] = Field(default_factory=list)
    user_pins: list[NonEmptyStr] = Field(default_factory=list)
    user_exclusions: list[NonEmptyStr] = Field(default_factory=list)
    mandatory_dependencies: list[NonEmptyStr] = Field(default_factory=list)
    inclusion_reasons: dict[str, str] = Field(default_factory=dict)
    open_questions: list[NonEmptyStr] = Field(default_factory=list)
    key_warnings: list[NonEmptyStr] = Field(default_factory=list)
    stale_context: list[StaleContextMarker] = Field(default_factory=list)
    dead_ends: list[DeadEndSummary] = Field(default_factory=list)
    cached_tool_results: list[ToolResultCacheSummary] = Field(default_factory=list)
    frame_invalidation_rules: list[InvalidationRule] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
