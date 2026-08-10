from __future__ import annotations

import asyncio
from collections.abc import Sequence
from uuid import UUID, uuid4

import pytest
from pydantic_ai.messages import ModelMessage

from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.dependencies import PlannerDeps
from cognieda.agents.planner.model import PlannerModelResult
from cognieda.agents.planner.types import (
    PlannerAction,
    PlannerAnswerInput,
    PlannerDecision,
    PlannerErrorCode,
    PlannerModelInput,
    PlannerResponseDraft,
)
from cognieda.application.services import PlannerContextPreparer, select_planner_context
from cognieda.execution import (
    Capability,
    ExecutionFailure,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
)
from cognieda.infrastructure.persistence import SqlitePlannerResearchState
from cognieda.infrastructure.persistence.repositories import (
    DataProfileRepository,
    EvidenceRepository,
)
from cognieda.schemas.artifacts import (
    Assumption,
    DataProfile,
    Evidence,
    Objective,
    SessionFrame,
    Task,
)
from cognieda.schemas.common import EvidenceProvenance
from cognieda.schemas.enums import TaskStatus


class FakePlannerModel:
    def __init__(
        self,
        decision: PlannerDecision,
        *,
        answer: str = "The admitted Evidence reports 42 rows.",
    ) -> None:
        self.decision = decision
        self.answer_text = answer
        self.decision_inputs: list[PlannerModelInput] = []
        self.message_histories: list[tuple[ModelMessage, ...]] = []
        self.answer_inputs: list[PlannerAnswerInput] = []

    async def decide(
        self,
        model_input: PlannerModelInput,
        *,
        message_history: Sequence[ModelMessage] = (),
    ) -> PlannerModelResult[PlannerDecision]:
        self.decision_inputs.append(model_input)
        self.message_histories.append(tuple(message_history))
        return PlannerModelResult(output=self.decision, new_messages=())

    async def answer(
        self, answer_input: PlannerAnswerInput
    ) -> PlannerModelResult[PlannerResponseDraft]:
        self.answer_inputs.append(answer_input)
        return PlannerModelResult(
            output=PlannerResponseDraft(text=self.answer_text),
            new_messages=(),
        )


class FakeDispatcher:
    def __init__(
        self,
        status: ExecutionStatus,
        *,
        returned_task_id: UUID | None = None,
    ) -> None:
        self.status = status
        self.returned_task_id = returned_task_id
        self.requests: list[ExecutionRequest] = []

    async def dispatch(self, request: ExecutionRequest) -> ExecutionResult:
        self.requests.append(request)
        failure = None
        if self.status is not ExecutionStatus.SUCCEEDED:
            failure = ExecutionFailure(
                code=f"fake_{self.status.value}",
                message=f"Fake dispatcher {self.status.value} the requested work.",
            )
        return ExecutionResult(
            source_role="fake_data_explorer",
            task_id=self.returned_task_id or request.input.task.task_id,
            work_id="fake-work:1",
            status=self.status,
            limitations=["M3-A Evidence admission remains deferred."],
            failure=failure,
        )


def _planner(
    model: FakePlannerModel,
    dispatcher: FakeDispatcher,
    research_state: SqlitePlannerResearchState,
) -> Planner:
    return Planner(
        deps=PlannerDeps(dispatcher=dispatcher, research_state=research_state),
        planner_model=model,
    )


def _planning_context(
    research_state: SqlitePlannerResearchState,
    query: str,
    frame: SessionFrame | None = None,
):
    return PlannerContextPreparer(research_state).build(
        latest_request=query,
        selection=select_planner_context(frame or SessionFrame()),
    )


def _objective_frame(research_state: SqlitePlannerResearchState, text: str) -> SessionFrame:
    objective = research_state.create_objective(Objective(text=text))
    return SessionFrame(
        objective_ids=(objective.objective_id,),
        active_objective_id=objective.objective_id,
    )


def _data_decision(
    instruction: str,
    capability: Capability = Capability.DATA_ANALYSIS,
    *,
    objective_text: str | None = None,
) -> PlannerDecision:
    return PlannerDecision(
        action=PlannerAction.CREATE_OR_RUN_DATA_TASK,
        objective_text=objective_text,
        task_instruction=instruction,
        capability=capability,
    )


@pytest.mark.parametrize(
    ("instruction", "capability"),
    [
        ("Profile the active dataset.", Capability.DATA_PROFILING),
        ("Summarize monthly_spend.", Capability.DATA_ANALYSIS),
        ("Create a cleaned successor dataset.", Capability.DATA_TRANSFORMATION),
    ],
)
def test_typed_capability_selection_dispatches_one_bounded_canonical_task(
    instruction: str,
    capability: Capability,
    db_session,
) -> None:
    research_state = SqlitePlannerResearchState(db_session)
    status = (
        ExecutionStatus.BLOCKED
        if capability is Capability.DATA_TRANSFORMATION
        else ExecutionStatus.SUCCEEDED
    )
    dispatcher = FakeDispatcher(status)
    model = FakePlannerModel(_data_decision(instruction, capability))
    frame = _objective_frame(research_state, "Understand the active dataset.")

    output = asyncio.run(
        _planner(model, dispatcher, research_state).run(
            "Do the requested bounded data work.",
            planning_context=_planning_context(
                research_state, "Do the requested bounded data work.", frame
            ),
            session_frame=frame,
        )
    )

    assert output.selected_capability is capability
    assert len(output.created_task_ids) == 1
    assert output.session_frame.task_ids == output.created_task_ids
    request = dispatcher.requests[0]
    assert request.capability is capability
    assert request.input.task.task_id == output.created_task_ids[0]
    assert request.input.task.instruction == instruction
    assert request.input.task.status is TaskStatus.RUNNING
    assert output.session_frame.evidence_ids == ()


def test_successful_work_updates_authoritative_task_without_replacing_frame_id(
    db_session,
) -> None:
    research_state = SqlitePlannerResearchState(db_session)
    instruction = "Summarize missingness by column."
    dispatcher = FakeDispatcher(ExecutionStatus.SUCCEEDED)
    model = FakePlannerModel(_data_decision(instruction))
    frame = _objective_frame(research_state, "Assess dataset quality.")

    output = asyncio.run(
        _planner(model, dispatcher, research_state).run(
            "Check missingness.",
            planning_context=_planning_context(research_state, "Check missingness.", frame),
            session_frame=frame,
        )
    )

    task_id = output.created_task_ids[0]
    task = research_state.get_task(task_id)
    assert task is not None
    assert task.status is TaskStatus.COMPLETED
    assert task.instruction == instruction
    assert output.session_frame.task_ids == (task_id,)
    assert output.work_outcome is not None
    assert output.work_outcome.status is ExecutionStatus.SUCCEEDED
    assert len(output.work_outcome.result_digest) == 64
    assert output.session_frame.evidence_ids == ()
    assert "No Evidence was admitted" in output.response


@pytest.mark.parametrize("status", [ExecutionStatus.FAILED, ExecutionStatus.BLOCKED])
def test_failed_or_blocked_work_fails_authoritative_task_without_evidence(
    status: ExecutionStatus,
    db_session,
) -> None:
    research_state = SqlitePlannerResearchState(db_session)
    dispatcher = FakeDispatcher(status)
    model = FakePlannerModel(_data_decision("Transform the active dataset."))
    frame = _objective_frame(research_state, "Prepare data for analysis.")

    output = asyncio.run(
        _planner(model, dispatcher, research_state).run(
            "Transform the data.",
            planning_context=_planning_context(
                research_state, "Transform the data.", frame
            ),
            session_frame=frame,
        )
    )

    task = research_state.get_task(output.session_frame.task_ids[-1])
    assert task is not None
    assert task.status is TaskStatus.FAILED
    assert output.work_outcome is not None
    assert output.work_outcome.status is status
    assert output.work_outcome.blockers == [f"Fake dispatcher {status.value} the requested work."]
    assert output.session_frame.evidence_ids == ()
    assert "No Evidence was created" in output.response


def test_task_outcome_identity_mismatch_fails_closed(db_session) -> None:
    research_state = SqlitePlannerResearchState(db_session)
    dispatcher = FakeDispatcher(ExecutionStatus.SUCCEEDED, returned_task_id=uuid4())
    model = FakePlannerModel(_data_decision("Profile the active dataset."))
    frame = _objective_frame(research_state, "Understand the data.")

    output = asyncio.run(
        _planner(model, dispatcher, research_state).run(
            "Profile the data.",
            planning_context=_planning_context(research_state, "Profile the data.", frame),
            session_frame=frame,
        )
    )

    assert output.error is not None
    assert output.error.code is PlannerErrorCode.TASK_OUTCOME_MISMATCH
    task = research_state.get_task(output.created_task_ids[0])
    assert task is not None
    assert task.status is TaskStatus.FAILED
    assert output.session_frame.evidence_ids == ()


def test_data_work_without_objective_returns_blocker_without_creating_task(
    db_session,
) -> None:
    research_state = SqlitePlannerResearchState(db_session)
    dispatcher = FakeDispatcher(ExecutionStatus.SUCCEEDED)
    model = FakePlannerModel(_data_decision("Profile the active dataset."))

    output = asyncio.run(
        _planner(model, dispatcher, research_state).run(
            "Profile it.",
            planning_context=_planning_context(research_state, "Profile it."),
        )
    )

    assert output.error is not None
    assert output.error.code is PlannerErrorCode.MISSING_OBJECTIVE
    assert output.created_task_ids == ()
    assert output.session_frame.task_ids == ()
    assert dispatcher.requests == []


def test_clear_data_request_establishes_objective_before_creating_task(db_session) -> None:
    research_state = SqlitePlannerResearchState(db_session)
    dispatcher = FakeDispatcher(ExecutionStatus.SUCCEEDED)
    model = FakePlannerModel(
        _data_decision(
            "Profile the active dataset.",
            Capability.DATA_PROFILING,
            objective_text="Understand the active dataset schema and quality.",
        )
    )

    output = asyncio.run(
        _planner(model, dispatcher, research_state).run(
            "Understand this dataset by profiling its schema and quality.",
            planning_context=_planning_context(
                research_state,
                "Understand this dataset by profiling its schema and quality.",
            ),
        )
    )

    assert output.session_frame.active_objective_id is not None
    objective = research_state.get_objective(output.session_frame.active_objective_id)
    task = research_state.get_task(output.session_frame.task_ids[0])
    assert objective is not None
    assert objective.text == "Understand the active dataset schema and quality."
    assert task is not None
    assert task.status is TaskStatus.COMPLETED


def test_semantic_task_change_creates_new_identity_without_rewriting_existing(
    db_session,
) -> None:
    research_state = SqlitePlannerResearchState(db_session)
    objective = research_state.create_objective(Objective(text="Understand dataset."))
    existing = research_state.create_task(Task(instruction="Profile the dataset."))
    frame = SessionFrame(
        objective_ids=(objective.objective_id,),
        active_objective_id=objective.objective_id,
        task_ids=(existing.task_id,),
    )
    dispatcher = FakeDispatcher(ExecutionStatus.SUCCEEDED)
    model = FakePlannerModel(_data_decision("Summarize missingness by column."))

    output = asyncio.run(
        _planner(model, dispatcher, research_state).run(
            "Now inspect missingness.",
            planning_context=_planning_context(
                research_state, "Now inspect missingness.", frame
            ),
            session_frame=frame,
        )
    )

    assert len(output.session_frame.task_ids) == 2
    old_task = research_state.get_task(output.session_frame.task_ids[0])
    new_task = research_state.get_task(output.session_frame.task_ids[1])
    assert old_task == existing
    assert new_task is not None
    assert new_task.task_id != existing.task_id
    assert new_task.instruction == "Summarize missingness by column."
    assert new_task.status is TaskStatus.COMPLETED


def test_explicit_assumption_addition_persists_then_retains_only_id(db_session) -> None:
    research_state = SqlitePlannerResearchState(db_session)
    dispatcher = FakeDispatcher(ExecutionStatus.SUCCEEDED)
    model = FakePlannerModel(PlannerDecision(action=PlannerAction.STATE_SUMMARY))
    frame = _objective_frame(research_state, "Understand churn.")

    output = asyncio.run(
        _planner(model, dispatcher, research_state).run(
            "/assumption Rows represent customers.",
            planning_context=_planning_context(
                research_state, "/assumption Rows represent customers.", frame
            ),
            session_frame=frame,
        )
    )

    assert frame.assumption_ids == ()
    assert len(output.session_frame.assumption_ids) == 1
    assumption = research_state.get_assumption(output.session_frame.assumption_ids[0])
    assert assumption is not None
    assert assumption.text == "Rows represent customers."
    assert output.session_frame.evidence_ids == ()
    assert "not empirical Evidence" in output.response
    assert dispatcher.requests == []
    assert model.decision_inputs == []


def _frame_with_admitted_evidence(
    db_session,
) -> tuple[SessionFrame, Evidence, SqlitePlannerResearchState]:
    research_state = SqlitePlannerResearchState(db_session)
    objective = research_state.create_objective(Objective(text="Understand dataset size."))
    task = research_state.create_task(Task(instruction="Count rows.", status=TaskStatus.COMPLETED))
    profile = DataProfileRepository(db_session).create(
        DataProfile(row_count=42, column_count=0, columns=())
    )
    evidence = EvidenceRepository(db_session).create(
        Evidence(
            task_id=task.task_id,
            data_profile_id=profile.data_profile_id,
            content={"row_count": 42},
            provenance=EvidenceProvenance(
                producer_role="data_explorer",
                work_reference="work:count-rows",
                dataset_reference="dataset:v1",
                data_profile_id=profile.data_profile_id,
                tool_reference="pandas:len",
            ),
        )
    )
    frame = SessionFrame(
        objective_ids=(objective.objective_id,),
        active_objective_id=objective.objective_id,
        task_ids=(task.task_id,),
        data_profile_ids=(profile.data_profile_id,),
        active_data_profile_id=profile.data_profile_id,
        evidence_ids=(evidence.evidence_id,),
    )
    return frame, evidence, research_state


def test_follow_up_answer_uses_admitted_typed_evidence(db_session) -> None:
    frame, evidence, research_state = _frame_with_admitted_evidence(db_session)
    model = FakePlannerModel(PlannerDecision(action=PlannerAction.ANSWER_FROM_STATE))
    dispatcher = FakeDispatcher(ExecutionStatus.SUCCEEDED)

    output = asyncio.run(
        _planner(model, dispatcher, research_state).run(
            "How many rows are in the dataset?",
            planning_context=_planning_context(
                research_state, "How many rows are in the dataset?", frame
            ),
            session_frame=frame,
        )
    )

    assert output.response == "The admitted Evidence reports 42 rows."
    assert output.session_frame == frame
    answer_input = model.answer_inputs[0]
    assert answer_input.latest_request == "How many rows are in the dataset?"
    assert answer_input.evidences == (evidence,)
    assert "assumptions" not in PlannerAnswerInput.model_fields
    assert dispatcher.requests == []


def test_assumption_only_claim_cannot_support_empirical_answer(db_session) -> None:
    research_state = SqlitePlannerResearchState(db_session)
    objective = research_state.create_objective(Objective(text="Understand dataset size."))
    assumption = research_state.create_assumption(Assumption(text="The dataset has 42 rows."))
    frame = SessionFrame(
        objective_ids=(objective.objective_id,),
        active_objective_id=objective.objective_id,
        assumption_ids=(assumption.assumption_id,),
    )
    model = FakePlannerModel(PlannerDecision(action=PlannerAction.ANSWER_FROM_STATE))
    dispatcher = FakeDispatcher(ExecutionStatus.SUCCEEDED)

    output = asyncio.run(
        _planner(model, dispatcher, research_state).run(
            "How many rows are in the dataset?",
            planning_context=_planning_context(
                research_state, "How many rows are in the dataset?", frame
            ),
            session_frame=frame,
        )
    )

    assert output.error is not None
    assert output.error.code is PlannerErrorCode.NO_ADMITTED_EVIDENCE
    assert "current bounded context" in output.response
    assert model.answer_inputs == []
    assert dispatcher.requests == []
