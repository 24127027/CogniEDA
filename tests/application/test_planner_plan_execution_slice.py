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


class AssumptionGateModel:
    def __init__(self, decision: PlannerDecision) -> None:
        self.decision = decision
        self.inputs: list[PlannerModelInput] = []

    async def decide(
        self,
        model_input: PlannerModelInput,
        *,
        message_history: Sequence[ModelMessage] = (),
    ) -> PlannerModelResult[PlannerDecision]:
        del message_history
        self.inputs.append(model_input)
        return PlannerModelResult(output=self.decision, new_messages=())

    async def answer(
        self,
        answer_input: PlannerAnswerInput,
    ) -> PlannerModelResult[PlannerResponseDraft]:
        raise AssertionError(f"Assumption handling cannot answer from Evidence: {answer_input}")


def _application(
    tmp_path,
    db_session: Session,
    *,
    planner_model: OneDataPlanModel | AssumptionGateModel | None = None,
) -> Application:
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
        planner_model=planner_model or OneDataPlanModel(),
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

    pending_objective = application._pending_objective
    pending_tasks = application._pending_tasks
    pending_revision = application._pending_plan_revision
    assert pending_objective is not None
    assert pending_tasks
    assert pending_revision is not None
    assert str(pending_revision.plan_revision_id) in proposal.content
    assert _authoritative_counts(db_session) == (0, 0, 0, 0)
    assert application.session_frame.objective is None
    assert application.session_frame.tasks == ()

    response = asyncio.run(application.submit_message("/approve"))

    assert application._pending_objective is None
    assert application._pending_tasks == ()
    assert application._pending_plan_revision is None
    assert application.session_frame.objective == pending_objective
    assert len(application.session_frame.tasks) == 1
    completed_task = application.session_frame.tasks[0]
    assert completed_task.task_id == pending_tasks[0].task_id
    assert completed_task.status is TaskStatus.COMPLETED
    assert TaskRepository(db_session).get_by_id(completed_task.task_id) == completed_task
    assert _authoritative_counts(db_session) == (1, 1, 1, 0)
    assert 'Result: {"row_count": 4}' in response.content
    assert "not admitted as Evidence" in response.content


def test_rejected_transient_plan_never_creates_or_executes_authoritative_work(
    tmp_path,
    db_session: Session,
) -> None:
    application = _application(tmp_path, db_session)
    asyncio.run(application.submit_message("How many rows are in this customer dataset?"))
    pending_revision = application._pending_plan_revision
    assert pending_revision is not None

    response = asyncio.run(application.submit_message("/reject"))

    assert application._pending_plan_revision is None
    assert "No authoritative Task or PlanRevision was created" in response.content
    assert _authoritative_counts(db_session) == (0, 0, 0, 0)
    assert application.session_frame.objective is None
    assert application.session_frame.tasks == ()


def test_approval_and_rejection_without_pending_plan_fail_cleanly(
    tmp_path,
    db_session: Session,
) -> None:
    application = _application(tmp_path, db_session)

    approval = asyncio.run(application.submit_message("/approve"))
    rejection = asyncio.run(application.submit_message("/reject"))

    assert "No plan is pending Human approval" in approval.content
    assert "No plan is pending Human rejection" in rejection.content
    assert _authoritative_counts(db_session) == (0, 0, 0, 0)


def test_second_proposal_cannot_replace_the_exact_pending_objects(
    tmp_path,
    db_session: Session,
) -> None:
    application = _application(tmp_path, db_session)
    asyncio.run(application.submit_message("How many rows are in this customer dataset?"))
    first_objective = application._pending_objective
    first_tasks = application._pending_tasks
    first_revision = application._pending_plan_revision

    response = asyncio.run(
        application.submit_message("Propose a later regenerated version of that plan.")
    )

    assert "already pending Human approval" in response.content
    assert application._pending_objective is first_objective
    assert application._pending_tasks is first_tasks
    assert application._pending_plan_revision is first_revision
    assert _authoritative_counts(db_session) == (0, 0, 0, 0)

    asyncio.run(application.submit_message("/approve"))

    assert application.session_frame.objective == first_objective
    assert application.session_frame.tasks[0].task_id == first_tasks[0].task_id


def test_explicit_non_testable_human_assumption_passes_gate_without_execution(
    tmp_path,
    db_session: Session,
) -> None:
    model = AssumptionGateModel(
        PlannerDecision(
            action=PlannerAction.ADD_ASSUMPTION,
            assumption_text="Customer intent is stable during this study.",
            assumption_is_reasonably_testable=False,
        )
    )
    application = _application(tmp_path, db_session, planner_model=model)

    response = asyncio.run(
        application.submit_message(
            "/assumption Customer intent is stable during this study."
        )
    )

    assert model.inputs[0].latest_request.startswith("/assumption")
    assert len(application.session_frame.assumptions) == 1
    assert application.session_frame.assumptions[0].text == (
        "Customer intent is stable during this study."
    )
    assert application.session_frame.evidences == ()
    assert application._pending_plan_revision is None
    assert "not reasonably testable" in response.content
    assert _authoritative_counts(db_session) == (0, 0, 0, 0)


def test_explicit_testable_human_claim_never_enters_assumption_state(
    tmp_path,
    db_session: Session,
) -> None:
    model = AssumptionGateModel(
        PlannerDecision(
            action=PlannerAction.INVALID_OR_UNSUPPORTED,
            assumption_text="Rows correspond to unique customers.",
            assumption_is_reasonably_testable=True,
        )
    )
    application = _application(tmp_path, db_session, planner_model=model)

    response = asyncio.run(
        application.submit_message(
            "/assumption Rows correspond to unique customers."
        )
    )

    assert application.session_frame.assumptions == ()
    assert application.session_frame.evidences == ()
    assert application._pending_plan_revision is None
    assert "scientific investigation" in response.content
    assert "not executable in the current DATA-only runtime" in response.content
    assert _authoritative_counts(db_session) == (0, 0, 0, 0)
