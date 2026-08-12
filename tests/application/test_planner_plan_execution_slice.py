from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import cast

import pandas as pd
from pydantic_ai.messages import ModelMessage
from sqlmodel import Session, select

from cognieda.agents.data_explorer import (
    DataAnalysisOperation,
    DataAnalysisPlan,
    DataAnalysisPlanningRequest,
    DataExplorer,
)
from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.dependencies import PlannerDeps
from cognieda.agents.planner.model import PlannerModelResult
from cognieda.agents.planner.types import (
    PlannerAction,
    PlannerAnswerInput,
    PlannerDecision,
    PlannerModelInput,
    PlannerResponseDraft,
)
from cognieda.application.ports import AgentFactoryPort
from cognieda.application.services import MvpDataProfileAdmissionService
from cognieda.execution import Capability, ExecutorDispatcher, ExecutorRegistry
from cognieda.infrastructure.persistence.models import (
    ActivePlanRevisionRecord,
    EvidenceRecord,
    PlanRevisionRecord,
    TaskRecord,
)
from cognieda.infrastructure.persistence.repositories import TaskRepository
from cognieda.runtime.application import Application
from cognieda.runtime.workspace import Workspace
from cognieda.schemas.enums import TaskStatus


class RowCountPlanner:
    async def propose(self, request: DataAnalysisPlanningRequest) -> DataAnalysisPlan:
        assert request.task_instruction == "Count rows in the active dataset."
        return DataAnalysisPlan(operation=DataAnalysisOperation.ROW_COUNT)


class OneDataPlanModel:
    async def decide(
        self,
        model_input: PlannerModelInput,
        *,
        message_history: Sequence[ModelMessage] = (),
    ) -> PlannerModelResult[PlannerDecision]:
        del message_history
        return PlannerModelResult(
            output=PlannerDecision(
                action=PlannerAction.CREATE_OR_RUN_DATA_TASK,
                objective_text="Establish the exact active dataset size.",
                task_instruction="Count rows in the active dataset.",
                capability=Capability.DATA_ANALYSIS,
            ),
            new_messages=(),
        )

    async def answer(
        self, answer_input: PlannerAnswerInput
    ) -> PlannerModelResult[PlannerResponseDraft]:
        raise AssertionError(f"Computed DATA output is not admitted Evidence: {answer_input}")


def _application(tmp_path, db_session: Session) -> Application:
    dataset_path = tmp_path / "customers.csv"
    pd.DataFrame(
        {
            "customer_id": [1, 2, 3, 4],
            "segment": ["a", "a", "b", "b"],
        }
    ).to_csv(dataset_path, index=False)

    data_explorer = DataExplorer(analysis_planner=RowCountPlanner())
    admitted = MvpDataProfileAdmissionService(db_session).admit_candidate(
        data_explorer.profile_candidate(str(dataset_path.resolve()))
    )
    registry = ExecutorRegistry()
    registry.register_provider(
        lambda: data_explorer,
        capabilities=(
            Capability.DATA_ANALYSIS,
            Capability.DATA_PROFILING,
            Capability.DATA_TRANSFORMATION,
        ),
    )
    dispatcher = ExecutorDispatcher(registry)
    planner = Planner(
        deps=PlannerDeps(dispatcher=dispatcher),
        planner_model=OneDataPlanModel(),
    )
    application = Application(
        workspace=cast(Workspace, object()),
        planner_agent=planner,
        dispatcher=dispatcher,
        agent_factory=cast(AgentFactoryPort, object()),
        session=db_session,
    )
    application.session_frame = application.session_frame.set_data_profile(
        admitted.data_profile
    )
    return application


def _authoritative_counts(session: Session) -> tuple[int, int, int, int]:
    return (
        len(session.exec(select(TaskRecord)).all()),
        len(session.exec(select(PlanRevisionRecord)).all()),
        len(session.exec(select(ActivePlanRevisionRecord)).all()),
        len(session.exec(select(EvidenceRecord)).all()),
    )


def test_approved_planner_data_plan_executes_real_work_end_to_end(
    tmp_path,
    db_session: Session,
) -> None:
    application = _application(tmp_path, db_session)

    proposal = asyncio.run(
        application.submit_message("How many rows are in this customer dataset?")
    )

    draft = application.pending_plan_draft
    assert draft is not None
    assert draft.fingerprint in proposal.content
    assert _authoritative_counts(db_session) == (0, 0, 0, 0)
    assert application.session_frame.objective is None
    assert application.session_frame.tasks == ()

    response = asyncio.run(
        application.submit_message(f"/approve {draft.fingerprint}")
    )

    assert application.pending_plan_draft is None
    assert application.session_frame.objective == draft.objective
    assert len(application.session_frame.tasks) == 1
    completed_task = application.session_frame.tasks[0]
    assert completed_task.status is TaskStatus.COMPLETED
    assert TaskRepository(db_session).get_by_id(completed_task.task_id) == completed_task
    assert _authoritative_counts(db_session) == (1, 1, 1, 0)
    assert 'Result: {"row_count": 4}' in response.content
    assert "not admitted as Evidence" in response.content


def test_rejected_plan_draft_never_creates_or_executes_authoritative_work(
    tmp_path,
    db_session: Session,
) -> None:
    application = _application(tmp_path, db_session)
    asyncio.run(application.submit_message("How many rows are in this customer dataset?"))
    draft = application.pending_plan_draft
    assert draft is not None

    response = asyncio.run(
        application.submit_message(f"/reject {draft.fingerprint}")
    )

    assert application.pending_plan_draft is None
    assert "No authoritative Task or PlanRevision was created" in response.content
    assert _authoritative_counts(db_session) == (0, 0, 0, 0)
    assert application.session_frame.objective is None
    assert application.session_frame.tasks == ()


def test_non_exact_approval_cannot_commit_or_execute_pending_draft(
    tmp_path,
    db_session: Session,
) -> None:
    application = _application(tmp_path, db_session)
    asyncio.run(application.submit_message("How many rows are in this customer dataset?"))
    draft = application.pending_plan_draft
    assert draft is not None

    response = asyncio.run(application.submit_message(f"/approve sha256:{'0' * 64}"))

    assert "did not match" in response.content
    assert application.pending_plan_draft is draft
    assert _authoritative_counts(db_session) == (0, 0, 0, 0)
