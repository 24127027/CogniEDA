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
    PlanDraft,
    PlanDraftApproval,
    PlanDraftDecision,
    PlanDraftDependency,
    PlanPriority,
    TaskDraft,
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


def _approve(db_session: Session, draft: PlanDraft) -> None:
    commit_approved_plan(
        db_session,
        plan_draft=draft,
        approval=PlanDraftApproval(
            plan_draft_id=draft.plan_draft_id,
            plan_draft_fingerprint=draft.fingerprint,
            decision=PlanDraftDecision.APPROVE,
        ),
    )


def test_dependency_precedes_priority_and_completed_tasks_are_not_rerun(
    tmp_path,
    db_session: Session,
) -> None:
    profile, registry = _profile_and_registry(tmp_path, db_session)
    prerequisite = TaskDraft(
        kind=TaskKind.DATA,
        instruction="First count rows.",
        required_capability=Capability.DATA_ANALYSIS,
        order_rank=10,
        priority=PlanPriority.LOW,
    )
    dependent = TaskDraft(
        kind=TaskKind.DATA,
        instruction="Then count rows again.",
        required_capability=Capability.DATA_ANALYSIS,
        order_rank=0,
        priority=PlanPriority.HIGH,
    )
    draft = PlanDraft(
        objective=Objective(text="Verify deterministic plan progression."),
        task_drafts=(dependent, prerequisite),
        dependencies=(
            PlanDraftDependency(
                prerequisite_task_draft_id=prerequisite.task_draft_id,
                dependent_task_draft_id=dependent.task_draft_id,
            ),
        ),
    )
    _approve(db_session, draft)
    executor = ActivePlanExecutor(db_session, ExecutorDispatcher(registry))

    first = asyncio.run(
        executor.execute_next(
            objective_id=draft.objective.objective_id,
            data_profile_id=profile.data_profile_id,
        )
    )
    second = asyncio.run(
        executor.execute_next(
            objective_id=draft.objective.objective_id,
            data_profile_id=profile.data_profile_id,
        )
    )

    assert first.task.task_id == prerequisite.task_draft_id
    assert second.task.task_id == dependent.task_draft_id
    with pytest.raises(ActivePlanExecutionError) as exc_info:
        asyncio.run(
            executor.execute_next(
                objective_id=draft.objective.objective_id,
                data_profile_id=profile.data_profile_id,
            )
        )
    assert exc_info.value.code is ActivePlanExecutionErrorCode.NO_ELIGIBLE_TASK


def test_unavailable_capability_returns_typed_non_success_without_fallback(
    tmp_path,
    db_session: Session,
) -> None:
    profile, _ = _profile_and_registry(tmp_path, db_session)
    task = TaskDraft(
        kind=TaskKind.DATA,
        instruction="Count rows.",
        required_capability=Capability.DATA_ANALYSIS,
        order_rank=0,
    )
    draft = PlanDraft(
        objective=Objective(text="Count rows."),
        task_drafts=(task,),
    )
    _approve(db_session, draft)

    result = asyncio.run(
        ActivePlanExecutor(
            db_session,
            ExecutorDispatcher(ExecutorRegistry()),
        ).execute_next(
            objective_id=draft.objective.objective_id,
            data_profile_id=profile.data_profile_id,
        )
    )

    assert result.planner_outcome.status is ExecutionStatus.BLOCKED
    assert result.planner_outcome.source_role == "application"
    assert "No provider registered" in result.planner_outcome.blockers[0]
