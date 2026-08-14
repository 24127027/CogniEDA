"""Application-owned execution session for semantic Planner tools."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from cognieda.agents.data_explorer.contracts import DataExplorerInput, DataExplorerResult
from cognieda.agents.planner.context import PlannerContext
from cognieda.application.ports import ExecutorDispatcherPort
from cognieda.application.services.mvp_data_admission import MvpEvidenceAdmissionService
from cognieda.execution import Capability, ExecutionRequest, ExecutionStatus, ExecutorContext
from cognieda.infrastructure.persistence.models import ActivePlanRecord, TaskRecord
from cognieda.infrastructure.persistence.repositories import (
    DataProfileDatasetBindingRepository,
    DataProfileRepository,
    PlanRepository,
    TaskRepository,
)
from cognieda.infrastructure.persistence.repositories.task_repository import TaskUpdate
from cognieda.schemas.artifacts import Evidence, Task
from cognieda.schemas.enums import TaskKind, TaskStatus
from cognieda.schemas.plan import Plan


class PlannerExecutionSession:
    """Execute against current persisted authority and expose typed successor context."""

    def __init__(
        self,
        session: Session,
        *,
        context: PlannerContext,
        active_plan: Plan,
    ) -> None:
        if context.active_plan != active_plan:
            raise ValueError("Execution context does not contain the exact active Plan.")
        self._session = session
        self._context = context
        self._active_plan = active_plan
        self._progress_count = 0

    @property
    def context(self) -> PlannerContext:
        return self._context

    @property
    def progress_count(self) -> int:
        return self._progress_count

    def _current_authorized_task(self, task_id: UUID) -> Task:
        active = self._session.get(
            ActivePlanRecord,
            self._active_plan.objective.objective_id,
        )
        if active is None or active.plan_id != self._active_plan.plan_id:
            raise ValueError("The requested Plan is not currently active.")
        persisted_plan = PlanRepository(self._session).get_by_id(active.plan_id)
        if persisted_plan != self._active_plan:
            raise ValueError("The active persisted Plan differs from execution context.")
        if self._context.objective != persisted_plan.objective:
            raise ValueError("Planner context does not contain the active Plan Objective.")
        if task_id not in persisted_plan.task_ids:
            raise ValueError("The requested Task is outside the active approved Plan.")

        tasks = TaskRepository(self._session)
        current_by_id: dict[UUID, Task] = {}
        for member_id in persisted_plan.task_ids:
            member = tasks.get_by_id(member_id)
            if member is None:
                raise ValueError("The active Plan references a missing authoritative Task.")
            current_by_id[member_id] = member
        context_by_id = {task.task_id: task for task in self._context.tasks}
        if context_by_id != current_by_id:
            raise ValueError("Planner context Task state is stale or incomplete.")
        completed = {
            member_id
            for member_id, member in current_by_id.items()
            if member.status is TaskStatus.COMPLETED
        }
        if task_id not in persisted_plan.eligible_task_ids(
            completed_task_ids=completed
        ):
            raise ValueError("The requested Task is not currently eligible in the Plan DAG.")

        task = current_by_id[task_id]
        if task.status is not TaskStatus.PENDING:
            raise ValueError("Only a currently PENDING Task may start DATA work.")
        if task.kind is not TaskKind.DATA:
            raise ValueError("run_data_work accepts only an approved DATA Task.")
        return task

    async def run_data_work(
        self,
        dispatcher: ExecutorDispatcherPort,
        *,
        task_id: UUID,
        requested_work: str,
    ) -> Evidence:
        """Dispatch one current eligible DATA Task and return admitted Evidence."""

        task = self._current_authorized_task(task_id)
        profile = self._context.data_profile
        if profile is None:
            raise ValueError("DATA work requires an active authoritative DataProfile.")
        persisted_profile = DataProfileRepository(self._session).get_by_id(
            profile.data_profile_id
        )
        if persisted_profile != profile:
            raise ValueError("Planner DataProfile context is not authoritative.")
        binding = DataProfileDatasetBindingRepository(
            self._session
        ).get_by_profile_id(profile.data_profile_id)
        if binding is None:
            raise ValueError("DATA work requires an authoritative dataset binding.")

        request = ExecutionRequest(
            capability=Capability.DATA_ANALYSIS,
            input=DataExplorerInput(
                task=task,
                data_profile=profile,
                requested_work=requested_work,
            ),
            context=ExecutorContext(
                dataset_path=binding.dataset_reference,
                data_profile_id=profile.data_profile_id,
            ),
        )
        task_record = self._session.get(TaskRecord, task.task_id)
        if task_record is None:
            raise ValueError("The requested Task disappeared before execution.")
        task_record.status = TaskStatus.RUNNING
        self._session.add(task_record)
        self._session.flush()

        try:
            result = await dispatcher.dispatch(request)
            if not isinstance(result, DataExplorerResult):
                raise TypeError("Data Explorer returned an incompatible result contract.")
            if result.status is not ExecutionStatus.SUCCEEDED:
                blocker = result.failure.message if result.failure is not None else "unknown"
                raise RuntimeError(f"Data Explorer did not complete the Task: {blocker}")

            task_record.status = TaskStatus.COMPLETED
            self._session.add(task_record)
            self._session.flush()
            admission = MvpEvidenceAdmissionService(self._session).admit(
                request,
                result,
                commit=False,
            )
            self._session.commit()
            completed_task = TaskRepository(self._session).get_by_id(task.task_id)
            if completed_task is None or completed_task.status is not TaskStatus.COMPLETED:
                raise RuntimeError("Committed DATA work did not retain a COMPLETED Task.")
            self._apply_task_and_evidence(completed_task, admission.evidence)
            self._progress_count += 1
            return admission.evidence
        except Exception:
            self._session.rollback()
            failed = TaskRepository(self._session).update(
                task.task_id,
                TaskUpdate(status=TaskStatus.FAILED),
            )
            if failed is not None:
                self._apply_task(failed)
                self._progress_count += 1
            raise

    def _apply_task(self, replacement: Task) -> None:
        tasks = tuple(
            replacement if task.task_id == replacement.task_id else task
            for task in self._context.tasks
        )
        self._context = self._context.model_copy(update={"tasks": tasks})

    def _apply_task_and_evidence(self, replacement: Task, evidence: Evidence) -> None:
        self._apply_task(replacement)
        evidences = self._context.evidences
        if all(item.evidence_id != evidence.evidence_id for item in evidences):
            evidences = (*evidences, evidence)
        self._context = self._context.model_copy(update={"evidences": evidences})


class PlannerExecutionSessionFactory:
    """Create per-execute sessions over the Application's authoritative database."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        context: PlannerContext,
        active_plan: Plan,
    ) -> PlannerExecutionSession:
        return PlannerExecutionSession(
            self._session,
            context=context,
            active_plan=active_plan,
        )


__all__ = ("PlannerExecutionSession", "PlannerExecutionSessionFactory")
