"""Typed semantic relation contracts for CogniEDA Knowledge Graph edges."""

from __future__ import annotations

from uuid import UUID

from cognieda.schemas.common import ImmutableCogniEDABaseModel
from cognieda.schemas.enums import ObjectiveHypothesisRelationType


class ObjectiveHypothesisRelation(ImmutableCogniEDABaseModel):
    """Immutable, non-FCO semantic graph edge connecting an Objective to a Hypothesis."""

    objective_id: UUID
    hypothesis_id: UUID
    relation_type: ObjectiveHypothesisRelationType


__all__ = (
    "ObjectiveHypothesisRelation",
    "ObjectiveHypothesisRelationType",
)
