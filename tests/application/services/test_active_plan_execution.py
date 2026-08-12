from __future__ import annotations

import asyncio

import pandas as pd
import pytest
from sqlmodel import Session

from cognieda.agents.data_explorer import (
    DataAnalysisOperation,
    DataAnalysisPlan,
    DataAnalysisPlanningRequest,
    DataExplorer,
)
from cognieda.application.services import (
    ActivePlanExecutionError,
    ActivePlanExecutionErrorCode,
    ActivePlanExecutor,
    MvpDataProfileAdmissionService,
    commit_approved_plan,
)
from cognieda.execution import (
    Capability,
    ExecutionStatus,
    ExecutorDispatcher,
    ExecutorRegistry,
)
from cognieda.schemas import (
    Objective,
    PlanDependency,
    PlanPriority,
    PlanRevision,
    PlanTaskBinding,
    Task,
    TaskKind,
)


class RowCountPlanner:
    async def propose(self, request: DataAnalysisPlanningRequest) -> DataAnalysisPlan:
        del request
        return DataAnalysisPlan(operation=DataAnalysisOperation.ROW_COUNT)


def _profile_and_registry(tmp_path, db_session: Session):
    dataset_path = tmp_path / "data.csv"
    pd.DataFrame({"value": [1, 2, 3]}).to_csv(dataset_path, index=False)
    explorer = DataExplorer(analysis_planner=RowCountPlanner())
    admitted = MvpDataProfileAdmissionService(db_session).admit_candidate(
        explorer.profile_candidate(str(dataset_path.resolve()))
    )
    registry = ExecutorRegistry()
    registry.register_provider(
        lambda: explorer,
        capabilities=(Capability.DATA_ANALYSIS,),
    )
    return admitted.data_profile, registry


def _approve(
    db_session: Session,
    objective: Objective,
    tasks: tuple[Task, ...],
    revision: PlanRevision,
) -> None:
    commit_approved_plan(
        db_session,
        objective=objective,
        tasks=tasks,
        plan_revision=revision,
    )


def test_dependency_precedes_priority_and_completed_tasks_are_not_rerun(
    tmp_path,
    db_session: Session,
) -> None:
    profile, registry = _profile_and_registry(tmp_path, db_session)
    objective = Objective(text="Verify deterministic plan progression.")
    prerequisite = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="First count rows.",
    )
    dependent = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="Then count rows again.",
    )
    tasks = (dependent, prerequisite)
    revision = PlanRevision.create(
        objective_id=objective.objective_id,
        task_bindings=(
            PlanTaskBinding(
                task_id=dependent.task_id,
                required_capability=Capability.DATA_ANALYSIS,
                order_rank=0,
                priority=PlanPriority.HIGH,
            ),
            PlanTaskBinding(
                task_id=prerequisite.task_id,
                required_capability=Capability.DATA_ANALYSIS,
                order_rank=10,
                priority=PlanPriority.LOW,
            ),
        ),
        dependencies=(
            PlanDependency(
                prerequisite_task_id=prerequisite.task_id,
                dependent_task_id=dependent.task_id,
            ),
        ),
        authoritative_tasks=tasks,
    )
    _approve(db_session, objective, tasks, revision)
    executor = ActivePlanExecutor(db_session, ExecutorDispatcher(registry))

    first = asyncio.run(
        executor.execute_next(
            objective_id=objective.objective_id,
            data_profile_id=profile.data_profile_id,
        )
    )
    second = asyncio.run(
        executor.execute_next(
            objective_id=objective.objective_id,
            data_profile_id=profile.data_profile_id,
        )
    )

    assert first.task.task_id == prerequisite.task_id
    assert second.task.task_id == dependent.task_id
    with pytest.raises(ActivePlanExecutionError) as exc_info:
        asyncio.run(
            executor.execute_next(
                objective_id=objective.objective_id,
                data_profile_id=profile.data_profile_id,
            )
        )
    assert exc_info.value.code is ActivePlanExecutionErrorCode.NO_ELIGIBLE_TASK


def test_unavailable_capability_returns_typed_non_success_without_fallback(
    tmp_path,
    db_session: Session,
) -> None:
    profile, _ = _profile_and_registry(tmp_path, db_session)
    objective = Objective(text="Count rows.")
    task = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="Count rows.",
    )
    revision = PlanRevision.create(
        objective_id=objective.objective_id,
        task_bindings=(
            PlanTaskBinding(
                task_id=task.task_id,
                required_capability=Capability.DATA_ANALYSIS,
                order_rank=0,
            ),
        ),
        authoritative_tasks=(task,),
    )
    _approve(db_session, objective, (task,), revision)

    result = asyncio.run(
        ActivePlanExecutor(
            db_session,
            ExecutorDispatcher(ExecutorRegistry()),
        ).execute_next(
            objective_id=objective.objective_id,
            data_profile_id=profile.data_profile_id,
        )
    )

    assert result.planner_outcome.status is ExecutionStatus.BLOCKED
    assert result.planner_outcome.source_role == "application"
    assert "No provider registered" in result.planner_outcome.blockers[0]
