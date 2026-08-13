from __future__ import annotations

import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pandas as pd
import pytest
from sqlmodel import Session

from cognieda.agents.data_explorer import (
    DataAnalysisOperation,
    DataAnalysisPlan,
    DataAnalysisPlanningRequest,
    DataExecutionProvenance,
    DataExplorer,
    DataExplorerObservation,
    DataExplorerResult,
)
from cognieda.agents.planner.dependencies import PlannerDeps
from cognieda.agents.planner.types import PlannerTaskExecutionOutput
from cognieda.application.planner_data_work import run_data_work
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
from cognieda.schemas.enums import TaskStatus


class RowCountPlanner:
    async def propose(self, request: DataAnalysisPlanningRequest) -> DataAnalysisPlan:
        del request
        return DataAnalysisPlan(operation=DataAnalysisOperation.ROW_COUNT)


class SemanticDataPlanner:
    def __init__(self, dispatcher: ExecutorDispatcher, *, invoke_tool: bool = True) -> None:
        self.dispatcher = dispatcher
        self.invoke_tool = invoke_tool
        self.task_ids = []

    async def execute_task(
        self,
        *,
        task,
        data_profile,
        execution_context,
        dataset_digest,
    ) -> PlannerTaskExecutionOutput:
        self.task_ids.append(task.task_id)
        deps = PlannerDeps(
            dispatcher=self.dispatcher,
            active_task=task,
            data_profile=data_profile,
            execution_context=execution_context,
            dataset_digest=dataset_digest,
        )
        if not self.invoke_tool:
            return PlannerTaskExecutionOutput(response="No governed work was needed.")
        outcome = await run_data_work(
            SimpleNamespace(deps=deps),  # type: ignore[arg-type]
            "Count rows to advance the approved Task.",
        )
        return PlannerTaskExecutionOutput(
            response=f"{outcome.semantic_summary} The result is not admitted Evidence.",
            blocker=outcome.blockers[0] if outcome.blockers else None,
            data_results=tuple(deps.data_results),
        )


class InvalidResultPlanner:
    def __init__(self, mode: str) -> None:
        self.mode = mode

    async def execute_task(
        self,
        *,
        task,
        data_profile,
        execution_context,
        dataset_digest,
    ) -> PlannerTaskExecutionOutput:
        result = DataExplorerResult(
            source_role="data_explorer",
            task_id=uuid4() if self.mode == "task" else task.task_id,
            work_id="invalid-result:1",
            status=ExecutionStatus.SUCCEEDED,
            capability=Capability.DATA_ANALYSIS,
            observations=[
                DataExplorerObservation(
                    observation_type="row_count",
                    summary="Counted rows.",
                    payload={"row_count": 3},
                )
            ],
            provenance=DataExecutionProvenance(
                dataset_reference=execution_context.dataset_path,
                dataset_digest=dataset_digest,
                data_profile_id=(
                    uuid4()
                    if self.mode == "profile"
                    else data_profile.data_profile_id
                ),
                tool_reference="test:row-count",
                operation=DataAnalysisOperation.ROW_COUNT,
            ),
            analysis_plan=DataAnalysisPlan(operation=DataAnalysisOperation.ROW_COUNT),
        )
        return PlannerTaskExecutionOutput(
            response="Invalid result must not complete the Task.",
            data_results=(result,),
        )


def _profile_and_dispatcher(tmp_path, db_session: Session):
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
    return admitted.data_profile, ExecutorDispatcher(registry)


def test_application_selects_dependencies_while_planner_pursues_each_task(
    tmp_path,
    db_session: Session,
) -> None:
    profile, dispatcher = _profile_and_dispatcher(tmp_path, db_session)
    objective = Objective(text="Verify plan progression.")
    prerequisite = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="First establish dataset size.",
    )
    dependent = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="Then confirm dataset size.",
    )
    tasks = (dependent, prerequisite)
    revision = PlanRevision.create(
        objective_id=objective.objective_id,
        task_bindings=(
            PlanTaskBinding(
                task_id=dependent.task_id,
                order_rank=0,
                priority=PlanPriority.HIGH,
            ),
            PlanTaskBinding(
                task_id=prerequisite.task_id,
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
        tasks=tasks,
    )
    commit_approved_plan(
        db_session,
        objective=objective,
        tasks=tasks,
        plan_revision=revision,
    )
    planner = SemanticDataPlanner(dispatcher)
    executor = ActivePlanExecutor(db_session)

    first = asyncio.run(
        executor.execute_next(
            planner=planner,  # type: ignore[arg-type]
            objective_id=objective.objective_id,
            data_profile_id=profile.data_profile_id,
        )
    )
    second = asyncio.run(
        executor.execute_next(
            planner=planner,  # type: ignore[arg-type]
            objective_id=objective.objective_id,
            data_profile_id=profile.data_profile_id,
        )
    )

    assert first.task.task_id == prerequisite.task_id
    assert second.task.task_id == dependent.task_id
    assert first.task.status is TaskStatus.COMPLETED
    assert second.task.status is TaskStatus.COMPLETED
    assert planner.task_ids == [prerequisite.task_id, dependent.task_id]
    with pytest.raises(ActivePlanExecutionError) as exc_info:
        asyncio.run(
            executor.execute_next(
                planner=planner,  # type: ignore[arg-type]
                objective_id=objective.objective_id,
                data_profile_id=profile.data_profile_id,
            )
        )
    assert exc_info.value.code is ActivePlanExecutionErrorCode.NO_ELIGIBLE_TASK


def test_application_does_not_complete_task_without_successful_governed_interaction(
    tmp_path,
    db_session: Session,
) -> None:
    profile, dispatcher = _profile_and_dispatcher(tmp_path, db_session)
    objective = Objective(text="Count rows.")
    task = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="Count rows.",
    )
    revision = PlanRevision.create(
        objective_id=objective.objective_id,
        task_bindings=(PlanTaskBinding(task_id=task.task_id, order_rank=0),),
        tasks=(task,),
    )
    commit_approved_plan(
        db_session,
        objective=objective,
        tasks=(task,),
        plan_revision=revision,
    )

    result = asyncio.run(
        ActivePlanExecutor(db_session).execute_next(
            planner=SemanticDataPlanner(  # type: ignore[arg-type]
                dispatcher,
                invoke_tool=False,
            ),
            objective_id=objective.objective_id,
            data_profile_id=profile.data_profile_id,
        )
    )

    assert result.task.status is TaskStatus.FAILED
    assert result.planner_execution.data_results == ()


@pytest.mark.parametrize(
    ("mode", "message"),
    [
        ("task", "identity does not match"),
        ("profile", "provenance does not match"),
    ],
)
def test_application_rejects_mismatched_planner_tool_results(
    tmp_path,
    db_session: Session,
    mode: str,
    message: str,
) -> None:
    profile, _ = _profile_and_dispatcher(tmp_path, db_session)
    objective = Objective(text="Validate governed result authority.")
    task = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="Count rows.",
    )
    revision = PlanRevision.create(
        objective_id=objective.objective_id,
        task_bindings=(PlanTaskBinding(task_id=task.task_id, order_rank=0),),
        tasks=(task,),
    )
    commit_approved_plan(
        db_session,
        objective=objective,
        tasks=(task,),
        plan_revision=revision,
    )

    result = asyncio.run(
        ActivePlanExecutor(db_session).execute_next(
            planner=InvalidResultPlanner(mode),  # type: ignore[arg-type]
            objective_id=objective.objective_id,
            data_profile_id=profile.data_profile_id,
        )
    )

    assert result.task.status is TaskStatus.FAILED
    assert result.planner_execution.blocker is not None
    assert message in result.planner_execution.blocker
