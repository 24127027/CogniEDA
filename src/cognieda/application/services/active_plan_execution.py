"""Execute the next eligible DATA Task from an explicit active PlanRevision."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from sqlmodel import Session

from cognieda.agents.data_explorer import DataExplorerInput, DataExplorerResult
from cognieda.application.ports import ExecutorDispatcherPort
from cognieda.execution import (
    ExecutionRequest,
    ExecutionStatus,
    ExecutorContext,
    PlannerWorkOutcome,
    normalize_for_planner,
)
from cognieda.execution.registry import CapabilityNotRegisteredError
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
    """Finite failures before a dispatcher request can be constructed."""

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
    """Terminal Task state plus role-native and Planner-facing execution results."""

    plan_revision: PlanRevision
    task: Task
    request: ExecutionRequest | None
    data_result: DataExplorerResult | None
    planner_outcome: PlannerWorkOutcome


def _task_with_status(task: Task, status: TaskStatus) -> Task:
    return Task(
        task_id=task.task_id,
        objective_id=task.objective_id,
        kind=task.kind,
        instruction=task.instruction,
        status=status,
    )


def _typed_blocked_outcome(task: Task, *, code: str, message: str) -> PlannerWorkOutcome:
    payload = json.dumps(
        {"task_id": str(task.task_id), "code": code, "message": message},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return PlannerWorkOutcome(
        source_role="application",
        task_id=task.task_id,
        work_id=f"blocked:{code}:{task.task_id}",
        status=ExecutionStatus.BLOCKED,
        semantic_summary="The active plan Task could not execute.",
        blockers=[message],
        permitted_next_actions=["hold", "replan"],
        result_digest=hashlib.sha256(payload).hexdigest(),
    )


class ActivePlanExecutor:
    """Simple deterministic scheduler for the current DATA-only runtime subset."""

    def __init__(self, session: Session, dispatcher: ExecutorDispatcherPort) -> None:
        self._session = session
        self._dispatcher = dispatcher
        self._active = ActivePlanRevisionRepository(session)
        self._revisions = PlanRevisionRepository(session)
        self._tasks = TaskRepository(session)
        self._profiles = DataProfileRepository(session)
        self._bindings = DataProfileDatasetBindingRepository(session)

    async def execute_next(
        self,
        *,
        objective_id: UUID,
        data_profile_id: UUID,
    ) -> ActivePlanExecutionResult:
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

        tasks_by_id: dict[UUID, Task] = {}
        for task_id in revision.task_ids:
            task = self._tasks.get_by_id(task_id)
            if task is None or task.objective_id != objective_id:
                raise ActivePlanExecutionError(
                    ActivePlanExecutionErrorCode.ACTIVE_PLAN_CORRUPT,
                    "Active PlanRevision membership does not resolve to authoritative Tasks.",
                )
            tasks_by_id[task_id] = task

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

        binding = next(
            item for item in revision.task_bindings if item.task_id == selected_task.task_id
        )
        if selected_task.kind is not TaskKind.DATA:
            return self._finish_blocked(
                revision,
                selected_task,
                code="unsupported_task_kind",
                message="The active MVP runtime executes only DATA Tasks.",
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
                "Eligible Task disappeared before dispatch.",
            )
        request = ExecutionRequest(
            capability=binding.required_capability,
            input=DataExplorerInput(task=running_task, data_profile=data_profile),
            context=ExecutorContext(
                dataset_path=dataset_binding.dataset_reference,
                data_profile_id=data_profile.data_profile_id,
            ),
        )

        try:
            dispatched = await self._dispatcher.dispatch(request)
        except CapabilityNotRegisteredError as exc:
            return self._finish_blocked(
                revision,
                running_task,
                request=request,
                code="capability_unavailable",
                message=str(exc),
            )
        except Exception as exc:
            return self._finish_blocked(
                revision,
                running_task,
                request=request,
                code="provider_failure",
                message=str(exc),
            )

        if not isinstance(dispatched, DataExplorerResult):
            return self._finish_blocked(
                revision,
                running_task,
                request=request,
                code="invalid_provider_result",
                message="DATA execution requires a role-native DataExplorerResult.",
            )
        if dispatched.task_id != running_task.task_id:
            return self._finish_blocked(
                revision,
                running_task,
                request=request,
                data_result=dispatched,
                code="task_outcome_mismatch",
                message="Executor result Task identity does not match the dispatched Task.",
            )
        provenance = dispatched.provenance
        if dispatched.status is ExecutionStatus.SUCCEEDED and (
            provenance is None
            or provenance.data_profile_id != data_profile_id
            or provenance.dataset_reference != dataset_binding.dataset_reference
            or provenance.dataset_digest != dataset_binding.dataset_digest
        ):
            return self._finish_blocked(
                revision,
                running_task,
                request=request,
                data_result=dispatched,
                code="dataset_binding_mismatch",
                message="Successful DATA output does not match authoritative dataset state.",
            )

        outcome = normalize_for_planner(dispatched)
        if dispatched.observations:
            outcome = outcome.model_copy(
                update={
                    "semantic_summary": " ".join(
                        f"{observation.summary} Result: "
                        f"{json.dumps(observation.payload, sort_keys=True)}"
                        for observation in dispatched.observations
                    )
                }
            )
        terminal_status = (
            TaskStatus.COMPLETED
            if dispatched.status is ExecutionStatus.SUCCEEDED
            else TaskStatus.FAILED
        )
        terminal_task = self._tasks.update(
            running_task.task_id,
            TaskUpdate(status=terminal_status),
        )
        if terminal_task is None:
            raise ActivePlanExecutionError(
                ActivePlanExecutionErrorCode.ACTIVE_PLAN_CORRUPT,
                "Dispatched Task disappeared before terminal persistence.",
            )
        return ActivePlanExecutionResult(
            plan_revision=revision,
            task=terminal_task,
            request=request,
            data_result=dispatched,
            planner_outcome=outcome,
        )

    def _finish_blocked(
        self,
        revision: PlanRevision,
        task: Task,
        *,
        code: str,
        message: str,
        request: ExecutionRequest | None = None,
        data_result: DataExplorerResult | None = None,
    ) -> ActivePlanExecutionResult:
        failed_task = self._tasks.update(task.task_id, TaskUpdate(status=TaskStatus.FAILED))
        if failed_task is None:
            failed_task = _task_with_status(task, TaskStatus.FAILED)
        return ActivePlanExecutionResult(
            plan_revision=revision,
            task=failed_task,
            request=request,
            data_result=data_result,
            planner_outcome=_typed_blocked_outcome(task, code=code, message=message),
        )


__all__ = (
    "ActivePlanExecutionError",
    "ActivePlanExecutionErrorCode",
    "ActivePlanExecutionResult",
    "ActivePlanExecutor",
)
