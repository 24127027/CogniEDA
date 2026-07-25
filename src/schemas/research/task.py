"""Canonical Task and AnalyticalSpecification research schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import Field, field_validator

from schemas.common import (
    CogniEDABaseModel,
    EvaluationThresholds,
    MethodParameter,
    NonEmptyStr,
    utc_now,
)
from schemas.research.lifecycle import (
    AnalysisIntent,
    TaskDependencyType,
    TaskKind,
    TaskLifecycleState,
)


class AnalyticalSpecification(CogniEDABaseModel):
    """Typed, non-FCO execution contract attached to an analytical Task."""

    hypothesis_statement: NonEmptyStr
    claim_type: Literal["association"]
    analysis_intent: AnalysisIntent = AnalysisIntent.EXPLORATORY
    data_profile_id: UUID
    variable_bindings: list[NonEmptyStr] = Field(min_length=1)
    scope: NonEmptyStr
    evidence_expectation: NonEmptyStr
    decision_rule: EvaluationThresholds
    validation_method: NonEmptyStr
    executor_id: Literal["deterministic"]
    method_parameters: list[MethodParameter] = Field(default_factory=list)
    deterministic_seed: int | None = None


class Task(CogniEDABaseModel):
    """Durable workflow state. A Task is not scientific knowledge."""

    task_id: UUID = Field(default_factory=uuid4)
    title: NonEmptyStr
    description: NonEmptyStr
    lifecycle_state: TaskLifecycleState = TaskLifecycleState.ACTIVE
    task_kind: TaskKind = TaskKind.ANALYTICAL
    parent_task_id: UUID | None = None
    dependency_type: TaskDependencyType | None = None
    blocked_reason: str | None = None
    superseded_by_task_id: UUID | None = None
    profile_id: UUID | None = None
    variables: list[NonEmptyStr] = Field(default_factory=list)
    evidence_expectation: str | None = None
    analytical_specification: AnalyticalSpecification | None = None
    motivated_by_discovery_ids: list[UUID] = Field(default_factory=list)
    review_reasons: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("motivated_by_discovery_ids")
    @classmethod
    def _validate_unique_discovery_ids(cls, v: list[UUID]) -> list[UUID]:
        if len(v) != len(set(v)):
            raise ValueError("motivated_by_discovery_ids must not contain duplicates")
        return v

    def can_generate_hypothesis(
        self,
        *,
        has_child_tasks: bool = False,
        data_profile_accepted: bool = True,
    ) -> bool:
        """Return whether this Task satisfies local hypothesis-admission guards."""

        return (
            self.lifecycle_state == TaskLifecycleState.ACTIVE
            and self.task_kind == TaskKind.ANALYTICAL
            and not has_child_tasks
            and data_profile_accepted
            and self.profile_id is not None
            and len(self.variables) > 0
            and bool(self.evidence_expectation)
        )
