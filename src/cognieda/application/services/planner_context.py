from __future__ import annotations

from collections.abc import Sequence
from typing import Never

from cognieda.agents.planner.context import (
    NonAuthoritativeSurfaceTurn,
    PlannerContextSelection,
    PlanningContext,
)
from cognieda.application.ports import PlannerResearchStatePort
from cognieda.schemas.artifacts import SessionFrame
from cognieda.schemas.enums import TaskStatus


class PlanningContextResolutionError(ValueError):
    """Selected session state could not become an eligible PlanningContext."""


def select_planner_context(
    frame: SessionFrame,
    *,
    recent_reference_limit: int = 20,
) -> PlannerContextSelection:
    """Select bounded per-run references from cumulative SessionFrame history."""

    if recent_reference_limit < 1:
        raise ValueError("recent_reference_limit must be positive.")
    return PlannerContextSelection(
        objective_id=frame.active_objective_id,
        assumption_ids=frame.assumption_ids[-recent_reference_limit:],
        task_ids=frame.task_ids[-recent_reference_limit:],
        active_data_profile_id=frame.active_data_profile_id,
        evidence_candidate_ids=frame.evidence_ids[-recent_reference_limit:],
    )


class PlannerContextPreparer:
    """Materialize one Planner run context through authoritative application state."""

    def __init__(self, research_state: PlannerResearchStatePort) -> None:
        self._research_state = research_state

    def build(
        self,
        *,
        latest_request: str,
        selection: PlannerContextSelection,
        surface_discourse: Sequence[NonAuthoritativeSurfaceTurn] = (),
    ) -> PlanningContext:
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
            latest_request=latest_request,
            objective=objective,
            assumptions=assumptions,
            tasks=tuple(tasks_by_id.values()),
            evidences=evidences,
            data_profile=data_profile,
            surface_discourse=tuple(surface_discourse),
        )

    @staticmethod
    def _required[ObjectT](object_name: str, object_id: object, value: ObjectT | None) -> ObjectT:
        if value is None:
            PlannerContextPreparer._missing(object_name, object_id)
        return value

    @staticmethod
    def _missing(object_name: str, object_id: object) -> Never:
        raise PlanningContextResolutionError(
            f"Context selection contains a missing {object_name} reference: {object_id}."
        )
