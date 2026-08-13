"""Execute the next eligible DATA Task from an explicit active PlanRevision."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from sqlmodel import Session

from cognieda.agents.data_explorer import DataExplorerResult
from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.types import PlannerTaskExecutionOutput
from cognieda.execution import ExecutionStatus, ExecutorContext
from cognieda.infrastructure.persistence.repositories import (
    ActivePlanRevisionRepository,
    DataProfileDatasetBindingRepository,
    DataProfileRepository,
    PlanRevisionRepository,
    TaskRepository,
)
from cognieda.infrastructure.persistence.repositories.task_repository import TaskUpdate
from cognieda.schemas.artifacts import Task
from cognieda.schemas.enums import TaskKind, TaskStatus
from cognieda.schemas.plan_revision import PlanRevision


class ActivePlanExecutionErrorCode(StrEnum):
    """Finite failures while resolving authoritative execution state."""

    ACTIVE_PLAN_NOT_FOUND = "active_plan_not_found"
    ACTIVE_PLAN_CORRUPT = "active_plan_corrupt"
    NO_ELIGIBLE_TASK = "no_eligible_task"
    DATA_PROFILE_NOT_FOUND = "data_profile_not_found"
    DATASET_BINDING_NOT_FOUND = "dataset_binding_not_found"


class ActivePlanExecutionError(ValueError):
    def __init__(self, code: ActivePlanExecutionErrorCode, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class ActivePlanExecutionResult:
    """Application-validated terminal state for one Planner Task interaction."""

    plan_revision: PlanRevision
    task: Task
    planner_execution: PlannerTaskExecutionOutput


def _task_with_status(task: Task, status: TaskStatus) -> Task:
    return Task(
        task_id=task.task_id,
        objective_id=task.objective_id,
        kind=task.kind,
        instruction=task.instruction,
        status=status,
    )


class ActivePlanExecutor:
    """Resolve eligibility and authority around Planner-led DATA interactions."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._active = ActivePlanRevisionRepository(session)
        self._revisions = PlanRevisionRepository(session)
        self._tasks = TaskRepository(session)
        self._profiles = DataProfileRepository(session)
        self._bindings = DataProfileDatasetBindingRepository(session)

    async def execute_next(
        self,
        *,
        planner: Planner,
        objective_id: UUID,
        data_profile_id: UUID,
    ) -> ActivePlanExecutionResult:
        revision = self._resolve_active_revision(objective_id)
        tasks_by_id = self._resolve_member_tasks(revision, objective_id)
        selected_task = self._select_eligible_task(revision, tasks_by_id)

        if selected_task.kind is not TaskKind.DATA:
            return self._finish_failed(
                revision,
                selected_task,
                response="The active MVP runtime executes only DATA Tasks.",
                blocker="The selected Task kind is not supported by this DATA-only runtime.",
            )

        data_profile = self._profiles.get_by_id(data_profile_id)
        if data_profile is None:
            raise ActivePlanExecutionError(
                ActivePlanExecutionErrorCode.DATA_PROFILE_NOT_FOUND,
                "DATA execution requires an authoritative DataProfile.",
            )
        dataset_binding = self._bindings.get_by_profile_id(data_profile_id)
        if dataset_binding is None:
            raise ActivePlanExecutionError(
                ActivePlanExecutionErrorCode.DATASET_BINDING_NOT_FOUND,
                "DATA execution requires an authoritative physical dataset binding.",
            )

        running_task = self._tasks.update(
            selected_task.task_id,
            TaskUpdate(status=TaskStatus.RUNNING),
        )
        if running_task is None:
            raise ActivePlanExecutionError(
                ActivePlanExecutionErrorCode.ACTIVE_PLAN_CORRUPT,
                "Eligible Task disappeared before Planner execution.",
            )

        try:
            planner_execution = await planner.execute_task(
                task=running_task,
                data_profile=data_profile,
                execution_context=ExecutorContext(
                    dataset_path=dataset_binding.dataset_reference,
                    data_profile_id=data_profile.data_profile_id,
                ),
                dataset_digest=dataset_binding.dataset_digest,
            )
            planner_execution = PlannerTaskExecutionOutput.model_validate(planner_execution)
            self._validate_data_results(
                planner_execution,
                task=running_task,
                data_profile_id=data_profile_id,
                dataset_reference=dataset_binding.dataset_reference,
                dataset_digest=dataset_binding.dataset_digest,
            )
        except Exception as exc:
            return self._finish_failed(
                revision,
                running_task,
                response="Planner could not complete the active DATA Task.",
                blocker=str(exc),
            )

        succeeded = any(
            result.status is ExecutionStatus.SUCCEEDED
            for result in planner_execution.data_results
        )
        terminal_status = (
            TaskStatus.COMPLETED
            if planner_execution.blocker is None and succeeded
            else TaskStatus.FAILED
        )
        terminal_task = self._tasks.update(
            running_task.task_id,
            TaskUpdate(status=terminal_status),
        )
        if terminal_task is None:
            raise ActivePlanExecutionError(
                ActivePlanExecutionErrorCode.ACTIVE_PLAN_CORRUPT,
                "Executed Task disappeared before terminal persistence.",
            )
        return ActivePlanExecutionResult(
            plan_revision=revision,
            task=terminal_task,
            planner_execution=planner_execution,
        )

    def _resolve_active_revision(self, objective_id: UUID) -> PlanRevision:
        selection = self._active.get_by_objective_id(objective_id)
        if selection is None:
            raise ActivePlanExecutionError(
                ActivePlanExecutionErrorCode.ACTIVE_PLAN_NOT_FOUND,
                "Execution requires an explicit active PlanRevision.",
            )
        revision = self._revisions.get_by_id(selection.plan_revision_id)
        if revision is None or revision.objective_id != objective_id:
            raise ActivePlanExecutionError(
                ActivePlanExecutionErrorCode.ACTIVE_PLAN_CORRUPT,
                "Active PlanRevision selection does not resolve to its Objective.",
            )
        return revision

    def _resolve_member_tasks(
        self,
        revision: PlanRevision,
        objective_id: UUID,
    ) -> dict[UUID, Task]:
        tasks_by_id: dict[UUID, Task] = {}
        for task_id in revision.task_ids:
            task = self._tasks.get_by_id(task_id)
            if task is None or task.objective_id != objective_id:
                raise ActivePlanExecutionError(
                    ActivePlanExecutionErrorCode.ACTIVE_PLAN_CORRUPT,
                    "Active PlanRevision membership does not resolve to authoritative Tasks.",
                )
            tasks_by_id[task_id] = task
        return tasks_by_id

    def _select_eligible_task(
        self,
        revision: PlanRevision,
        tasks_by_id: dict[UUID, Task],
    ) -> Task:
        completed_ids = {
            task_id
            for task_id, task in tasks_by_id.items()
            if task.status is TaskStatus.COMPLETED
        }
        eligible_ids = revision.eligible_task_ids(completed_task_ids=completed_ids)
        selected_task = next(
            (
                tasks_by_id[task_id]
                for task_id in eligible_ids
                if tasks_by_id[task_id].status is TaskStatus.PENDING
            ),
            None,
        )
        if selected_task is None:
            raise ActivePlanExecutionError(
                ActivePlanExecutionErrorCode.NO_ELIGIBLE_TASK,
                "The active PlanRevision has no eligible pending Task.",
            )
        return selected_task

    @staticmethod
    def _validate_data_results(
        planner_execution: PlannerTaskExecutionOutput,
        *,
        task: Task,
        data_profile_id: UUID,
        dataset_reference: str,
        dataset_digest: str,
    ) -> None:
        for result in planner_execution.data_results:
            if not isinstance(result, DataExplorerResult):
                raise ValueError("Planner DATA interactions require DataExplorerResult values.")
            if result.task_id != task.task_id or result.source_role != "data_explorer":
                raise ValueError(
                    "Data Explorer result identity does not match the eligible Task."
                )
            provenance = result.provenance
            if result.status is ExecutionStatus.SUCCEEDED and (
                provenance is None
                or provenance.data_profile_id != data_profile_id
                or provenance.dataset_reference != dataset_reference
                or provenance.dataset_digest != dataset_digest
            ):
                raise ValueError(
                    "Data Explorer result provenance does not match authoritative state."
                )

    def _finish_failed(
        self,
        revision: PlanRevision,
        task: Task,
        *,
        response: str,
        blocker: str,
    ) -> ActivePlanExecutionResult:
        failed_task = self._tasks.update(task.task_id, TaskUpdate(status=TaskStatus.FAILED))
        if failed_task is None:
            failed_task = _task_with_status(task, TaskStatus.FAILED)
        return ActivePlanExecutionResult(
            plan_revision=revision,
            task=failed_task,
            planner_execution=PlannerTaskExecutionOutput(
                response=response,
                blocker=blocker,
            ),
        )


__all__ = (
    "ActivePlanExecutionError",
    "ActivePlanExecutionErrorCode",
    "ActivePlanExecutionResult",
    "ActivePlanExecutor",
)
