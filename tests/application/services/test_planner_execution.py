from __future__ import annotations

import asyncio
from pathlib import Path

import pandas as pd
import pytest
from sqlmodel import Session

from cognieda.agents.data_explorer import (
    DataAnalysisOperation,
    DataAnalysisPlan,
    DataAnalysisPlanningRequest,
    DataExplorer,
)
from cognieda.agents.planner.context import PlannerContext
from cognieda.application.services import (
    MvpDataProfileAdmissionService,
    PlanAdmissionService,
    PlannerExecutionSessionFactory,
)
from cognieda.execution import Capability, ExecutorDispatcher, ExecutorRegistry
from cognieda.infrastructure.persistence.repositories import EvidenceRepository, TaskRepository
from cognieda.schemas import (
    Objective,
    Plan,
    PlanDependency,
    PlanTaskBinding,
    Task,
    TaskKind,
    TaskStatus,
)


class RecordingRowCountPlanner:
    def __init__(self) -> None:
        self.requests: list[DataAnalysisPlanningRequest] = []

    async def propose(self, request: DataAnalysisPlanningRequest) -> DataAnalysisPlan:
        self.requests.append(request)
        return DataAnalysisPlan(operation=DataAnalysisOperation.ROW_COUNT)


def _runtime(
    tmp_path: Path,
    db_session: Session,
    *,
    dependent: bool = False,
):
    dataset_path = tmp_path / "planner-execution.csv"
    pd.DataFrame({"value": [1, 2, 3]}).to_csv(dataset_path, index=False)
    candidate = DataExplorer().profile_candidate(str(dataset_path.resolve()))
    profile = MvpDataProfileAdmissionService(db_session).admit_candidate(candidate).data_profile

    objective = Objective(text="Characterize the current dataset.")
    first = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="Count the current rows.",
    )
    tasks = (first,)
    dependencies: tuple[PlanDependency, ...] = ()
    if dependent:
        second = Task(
            objective_id=objective.objective_id,
            kind=TaskKind.DATA,
            instruction="Verify the row count after the first bounded observation.",
        )
        tasks = (first, second)
        dependencies = (
            PlanDependency(
                prerequisite_task_id=first.task_id,
                dependent_task_id=second.task_id,
            ),
        )
    plan = Plan.create(
        objective=objective,
        task_bindings=tuple(
            PlanTaskBinding(task_id=task.task_id, order_rank=index)
            for index, task in enumerate(tasks)
        ),
        dependencies=dependencies,
        tasks=tasks,
    )
    PlanAdmissionService(db_session).admit(plan, tasks)

    analysis_planner = RecordingRowCountPlanner()
    registry = ExecutorRegistry()
    registry.register_provider(
        lambda: DataExplorer(analysis_planner=analysis_planner),
        capabilities=(Capability.DATA_ANALYSIS,),
    )
    dispatcher = ExecutorDispatcher(registry)
    context = PlannerContext(
        active_plan=plan,
        objective=objective,
        tasks=tasks,
        data_profile=profile,
    )
    execution = PlannerExecutionSessionFactory(db_session).create(
        context=context,
        active_plan=plan,
    )
    return execution, dispatcher, tasks, analysis_planner


def test_data_tool_returns_admitted_evidence_and_updates_successor_context(
    tmp_path: Path,
    db_session: Session,
) -> None:
    execution, dispatcher, tasks, analysis_planner = _runtime(tmp_path, db_session)
    task = tasks[0]

    evidence = asyncio.run(
        execution.run_data_work(
            dispatcher,
            task_id=task.task_id,
            requested_work="Count rows for the approved dataset scope.",
        )
    )

    assert analysis_planner.requests[0].task_instruction == (
        "Count rows for the approved dataset scope."
    )
    assert TaskRepository(db_session).get_by_id(task.task_id).status is TaskStatus.COMPLETED  # type: ignore[union-attr]
    assert EvidenceRepository(db_session).get_by_id(evidence.evidence_id) == evidence
    assert execution.context.tasks[0].status is TaskStatus.COMPLETED
    assert execution.context.evidences == (evidence,)
    assert execution.context.active_plan is not None
    assert execution.progress_count == 1


def test_eligibility_is_recomputed_after_each_authoritative_completion(
    tmp_path: Path,
    db_session: Session,
) -> None:
    execution, dispatcher, tasks, _ = _runtime(tmp_path, db_session, dependent=True)
    first, second = tasks

    with pytest.raises(ValueError, match="not currently eligible"):
        asyncio.run(
            execution.run_data_work(
                dispatcher,
                task_id=second.task_id,
                requested_work="Attempt dependent work too early.",
            )
        )

    asyncio.run(
        execution.run_data_work(
            dispatcher,
            task_id=first.task_id,
            requested_work="Complete the prerequisite row count.",
        )
    )
    asyncio.run(
        execution.run_data_work(
            dispatcher,
            task_id=second.task_id,
            requested_work="Now complete the dependent row count.",
        )
    )

    assert [task.status for task in execution.context.tasks] == [
        TaskStatus.COMPLETED,
        TaskStatus.COMPLETED,
    ]
    assert len(execution.context.evidences) == 2
    assert execution.progress_count == 2


def test_evidence_admission_failure_rolls_back_completion_and_fails_task(
    tmp_path: Path,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    execution, dispatcher, tasks, _ = _runtime(tmp_path, db_session)
    task = tasks[0]

    def reject_evidence(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("forced Evidence admission failure")

    monkeypatch.setattr(EvidenceRepository, "add", reject_evidence)

    with pytest.raises(RuntimeError, match="forced Evidence admission failure"):
        asyncio.run(
            execution.run_data_work(
                dispatcher,
                task_id=task.task_id,
                requested_work="Count rows before forced admission failure.",
            )
        )

    persisted = TaskRepository(db_session).get_by_id(task.task_id)
    assert persisted is not None and persisted.status is TaskStatus.FAILED
    assert EvidenceRepository(db_session).list(task_id=task.task_id) == []
    assert execution.context.tasks[0].status is TaskStatus.FAILED
    assert execution.context.evidences == ()
