"""Canonical Objective and ObjectiveRevision research schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import Field

from schemas.common import CogniEDABaseModel, NonEmptyStr, utc_now
from schemas.research.lifecycle import AnalysisIntent, ObjectiveStatus


class Objective(CogniEDABaseModel):
    """Research intent for one workspace graph."""

    objective_id: UUID = Field(default_factory=uuid4)
    title: NonEmptyStr
    statement: NonEmptyStr
    analysis_intent: AnalysisIntent = AnalysisIntent.EXPLORATORY
    status: ObjectiveStatus = ObjectiveStatus.ACTIVE
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ObjectiveRevision(CogniEDABaseModel):
    """Immutable non-FCO provenance for one governed Objective mutation."""

    objective_revision_id: UUID = Field(default_factory=uuid4)
    objective_id: UUID
    previous_title: NonEmptyStr
    previous_statement: NonEmptyStr
    previous_status: ObjectiveStatus
    new_title: NonEmptyStr
    new_statement: NonEmptyStr
    new_status: ObjectiveStatus
    changed_fields: list[NonEmptyStr]
    reason: NonEmptyStr
    planner_operation_id: UUID | None = None
    user_decision_id: UUID | None = None
    actor: NonEmptyStr
    created_at: datetime = Field(default_factory=utc_now)
