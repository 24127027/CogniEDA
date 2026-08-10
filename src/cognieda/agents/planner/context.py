from __future__ import annotations

from collections.abc import Sequence
from typing import Never
from uuid import UUID

from pydantic import ConfigDict, Field
from pydantic_ai.messages import ModelMessage

from cognieda.application.ports import PlannerResearchStatePort
from cognieda.schemas.artifacts import (
    Assumption,
    DataProfile,
    Evidence,
    Objective,
    SessionFrame,
    Task,
)
from cognieda.schemas.common import CogniEDABaseModel
from cognieda.schemas.enums import TaskStatus


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
    message_history: tuple[ModelMessage, ...] = ()


class PlannerContextSelection(CogniEDABaseModel):
    """Bounded references and whole-segment messages selected before materialization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    latest_request: str = Field(min_length=1)
    objective_id: UUID | None = None
    assumption_ids: tuple[UUID, ...] = ()
    task_ids: tuple[UUID, ...] = ()
    active_data_profile_id: UUID | None = None
    evidence_candidate_ids: tuple[UUID, ...] = ()
    surface_discourse: tuple[NonAuthoritativeSurfaceTurn, ...] = ()
    message_history: tuple[ModelMessage, ...] = ()


class PlannerContextSelector:
    """Apply the conservative finite MVP policy to cumulative session history."""

    def __init__(self, *, recent_reference_limit: int = 20) -> None:
        if recent_reference_limit < 1:
            raise ValueError("recent_reference_limit must be positive.")
        self._recent_reference_limit = recent_reference_limit

    def select(
        self,
        *,
        latest_request: str,
        frame: SessionFrame,
        surface_discourse: Sequence[NonAuthoritativeSurfaceTurn] = (),
        message_history: Sequence[ModelMessage] = (),
    ) -> PlannerContextSelection:
        """Select active refs plus bounded recent candidates without resolving them."""

        limit = self._recent_reference_limit
        return PlannerContextSelection(
            latest_request=latest_request,
            objective_id=frame.active_objective_id,
            assumption_ids=frame.assumption_ids[-limit:],
            task_ids=frame.task_ids[-limit:],
            active_data_profile_id=frame.active_data_profile_id,
            evidence_candidate_ids=frame.evidence_ids[-limit:],
            surface_discourse=tuple(surface_discourse),
            message_history=tuple(message_history),
        )


class PlanningContextResolutionError(ValueError):
    """A selected reference could not be resolved into eligible run context."""


class BuildPlanningContext:
    """Resolve selected refs, expand required dependencies, and materialize context."""

    def __init__(self, research_state: PlannerResearchStatePort) -> None:
        self._research_state = research_state

    def build(self, *, selection: PlannerContextSelection) -> PlanningContext:
        objective = None
        if selection.objective_id is not None:
            objective = self._research_state.get_objective(selection.objective_id)
            if objective is None:
                self._missing("Objective", selection.objective_id)

        assumptions = tuple(
            self._required(
                "Assumption",
                assumption_id,
                self._research_state.get_assumption(assumption_id),
            )
            for assumption_id in selection.assumption_ids
        )
        selected_tasks = [
            self._required("Task", task_id, self._research_state.get_task(task_id))
            for task_id in selection.task_ids
        ]

        active_profile = None
        if selection.active_data_profile_id is not None:
            active_profile = self._research_state.get_data_profile(
                selection.active_data_profile_id
            )
            if active_profile is None:
                self._missing("DataProfile", selection.active_data_profile_id)

        evidence_candidates = [
            self._required(
                "Evidence",
                evidence_id,
                self._research_state.get_evidence(evidence_id),
            )
            for evidence_id in selection.evidence_candidate_ids
        ]
        selected_profile_id = (
            active_profile.data_profile_id
            if active_profile is not None
            else (
                evidence_candidates[-1].data_profile_id if evidence_candidates else None
            )
        )
        evidences = tuple(
            evidence
            for evidence in evidence_candidates
            if evidence.data_profile_id == selected_profile_id
        )

        tasks_by_id = {task.task_id: task for task in selected_tasks}
        data_profile = active_profile
        for evidence in evidences:
            task = self._research_state.get_task(evidence.task_id)
            if task is None:
                self._missing("Evidence Task dependency", evidence.task_id)
            if task.status is not TaskStatus.COMPLETED:
                raise PlanningContextResolutionError(
                    "PlanningContext accepts Evidence only for an authoritative COMPLETED Task."
                )
            tasks_by_id.setdefault(task.task_id, task)

            evidence_profile = self._research_state.get_data_profile(evidence.data_profile_id)
            if evidence_profile is None:
                self._missing("Evidence DataProfile dependency", evidence.data_profile_id)
            if data_profile is None:
                data_profile = evidence_profile
            elif evidence_profile.data_profile_id != data_profile.data_profile_id:
                raise PlanningContextResolutionError(
                    "Selected Evidence dependencies must share the materialized DataProfile."
                )

        return PlanningContext(
            latest_request=selection.latest_request,
            objective=objective,
            assumptions=assumptions,
            tasks=tuple(tasks_by_id.values()),
            evidences=evidences,
            data_profile=data_profile,
            surface_discourse=selection.surface_discourse,
            message_history=selection.message_history,
        )

    @staticmethod
    def _required[ObjectT](object_name: str, object_id: object, value: ObjectT | None) -> ObjectT:
        if value is None:
            BuildPlanningContext._missing(object_name, object_id)
        return value

    @staticmethod
    def _missing(object_name: str, object_id: object) -> Never:
        raise PlanningContextResolutionError(
            f"Context selection contains a missing {object_name} reference: {object_id}."
        )
