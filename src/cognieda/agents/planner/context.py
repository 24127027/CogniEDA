from __future__ import annotations

from uuid import UUID

from pydantic import ConfigDict, Field

from cognieda.schemas.artifacts import (
    Assumption,
    DataProfile,
    Evidence,
    Objective,
    Task,
)
from cognieda.schemas.common import CogniEDABaseModel


class NonAuthoritativeSurfaceTurn(CogniEDABaseModel):
    """Selected Human/Planner discourse usable only for intent and reference resolution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    human_message: str = Field(min_length=1)
    planner_response: str = Field(min_length=1)


class PlanningContext(CogniEDABaseModel):
    """Ephemeral materialized research context selected for one Planner run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    latest_request: str = Field(min_length=1)
    objective: Objective | None = None
    assumptions: tuple[Assumption, ...] = ()
    tasks: tuple[Task, ...] = ()
    evidences: tuple[Evidence, ...] = ()
    data_profile: DataProfile | None = None
    surface_discourse: tuple[NonAuthoritativeSurfaceTurn, ...] = ()


class PlannerContextSelection(CogniEDABaseModel):
    """Bounded research-state references selected for one Planner run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    objective_id: UUID | None = None
    assumption_ids: tuple[UUID, ...] = ()
    task_ids: tuple[UUID, ...] = ()
    active_data_profile_id: UUID | None = None
    evidence_candidate_ids: tuple[UUID, ...] = ()
