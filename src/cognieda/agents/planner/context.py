from __future__ import annotations

from collections.abc import Sequence
from typing import Never

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


class PlanningContext(CogniEDABaseModel):
    """Ephemeral materialized research context selected for one Planner run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    latest_request: str = Field(min_length=1)
    objective: Objective | None = None
    assumptions: tuple[Assumption, ...] = ()
    tasks: tuple[Task, ...] = ()
    evidences: tuple[Evidence, ...] = ()
    data_profile: DataProfile | None = None
    message_history: tuple[ModelMessage, ...] = ()


class PlanningContextResolutionError(ValueError):
    """A SessionFrame reference could not be resolved into eligible run context."""


class BuildPlanningContext:
    """Resolve one SessionFrame reference manifest through authoritative repositories."""

    def __init__(self, research_state: PlannerResearchStatePort) -> None:
        self._research_state = research_state

    def build(
        self,
        *,
        latest_request: str,
        frame: SessionFrame,
        message_history: Sequence[ModelMessage] = (),
    ) -> PlanningContext:
        objective = None
        if frame.objective_id is not None:
            objective = self._research_state.get_objective(frame.objective_id)
            if objective is None:
                self._missing("Objective", frame.objective_id)

        assumptions = tuple(
            self._required(
                "Assumption",
                assumption_id,
                self._research_state.get_assumption(assumption_id),
            )
            for assumption_id in frame.assumption_ids
        )
        tasks = tuple(
            self._required("Task", task_id, self._research_state.get_task(task_id))
            for task_id in frame.task_ids
        )
        tasks_by_id = {task.task_id: task for task in tasks}

        data_profile = None
        if frame.data_profile_id is not None:
            data_profile = self._research_state.get_data_profile(frame.data_profile_id)
            if data_profile is None:
                self._missing("DataProfile", frame.data_profile_id)

        evidences = tuple(
            self._required("Evidence", evidence_id, self._research_state.get_evidence(evidence_id))
            for evidence_id in frame.evidence_ids
        )
        for evidence in evidences:
            task = tasks_by_id.get(evidence.task_id)
            if task is None:
                raise PlanningContextResolutionError(
                    "PlanningContext rejects Evidence whose authoritative Task is not "
                    "referenced by SessionFrame."
                )
            if task.status is not TaskStatus.COMPLETED:
                raise PlanningContextResolutionError(
                    "PlanningContext accepts Evidence only for an authoritative COMPLETED Task."
                )
            if data_profile is None:
                raise PlanningContextResolutionError(
                    "PlanningContext cannot select Evidence without a referenced DataProfile."
                )
            if evidence.data_profile_id != data_profile.data_profile_id:
                raise PlanningContextResolutionError(
                    "PlanningContext Evidence must match the referenced DataProfile."
                )

        return PlanningContext(
            latest_request=latest_request,
            objective=objective,
            assumptions=assumptions,
            tasks=tasks,
            evidences=evidences,
            data_profile=data_profile,
            message_history=tuple(message_history),
        )

    @staticmethod
    def _required[ObjectT](object_name: str, object_id: object, value: ObjectT | None) -> ObjectT:
        if value is None:
            BuildPlanningContext._missing(object_name, object_id)
        return value

    @staticmethod
    def _missing(object_name: str, object_id: object) -> Never:
        raise PlanningContextResolutionError(
            f"SessionFrame contains a missing {object_name} reference: {object_id}."
        )
