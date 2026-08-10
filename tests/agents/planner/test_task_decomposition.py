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
from cognieda.execution import (
    Capability,
    ExecutionFailure,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
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
        self.answer_inputs: list[PlannerAnswerInput] = []
        self.message_histories: list[tuple[ModelMessage, ...]] = []

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


def _planner(model: FakePlannerModel, dispatcher: FakeDispatcher) -> Planner:
    return Planner(
        deps=PlannerDeps(dispatcher=dispatcher),
        planner_model=model,
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
) -> None:
    status = (
        ExecutionStatus.BLOCKED
        if capability is Capability.DATA_TRANSFORMATION
        else ExecutionStatus.SUCCEEDED
    )
    dispatcher = FakeDispatcher(status)
    model = FakePlannerModel(_data_decision(instruction, capability))
    frame = SessionFrame(objective=Objective(text="Understand the active dataset."))

    output = asyncio.run(
        _planner(model, dispatcher).run("Do the requested bounded data work.", session_frame=frame)
    )

    assert output.selected_capability is capability
    assert len(output.created_task_ids) == 1
    assert len(dispatcher.requests) == 1
    request = dispatcher.requests[0]
    assert request.capability is capability
    assert request.input.task.task_id == output.created_task_ids[0]
    assert request.input.task.instruction == instruction
    assert request.input.task.status is TaskStatus.RUNNING
    assert output.session_frame.evidences == ()


def test_successful_work_preserves_task_identity_and_completes_without_evidence() -> None:
    instruction = "Summarize missingness by column."
    dispatcher = FakeDispatcher(ExecutionStatus.SUCCEEDED)
    model = FakePlannerModel(_data_decision(instruction))
    frame = SessionFrame(objective=Objective(text="Assess dataset quality."))

    output = asyncio.run(
        _planner(model, dispatcher).run("Check missingness.", session_frame=frame)
    )

    task_id = output.created_task_ids[0]
    task = next(task for task in output.session_frame.tasks if task.task_id == task_id)
    assert task.status is TaskStatus.COMPLETED
    assert task.instruction == instruction
    assert dispatcher.requests[0].input.task.task_id == task.task_id
    assert output.work_outcome is not None
    assert output.work_outcome.status is ExecutionStatus.SUCCEEDED
    assert len(output.work_outcome.result_digest) == 64
    assert output.session_frame.evidences == ()
    assert "No Evidence was admitted" in output.response


@pytest.mark.parametrize("status", [ExecutionStatus.FAILED, ExecutionStatus.BLOCKED])
def test_failed_or_blocked_work_fails_task_and_surfaces_blocker_without_evidence(
    status: ExecutionStatus,
) -> None:
    dispatcher = FakeDispatcher(status)
    model = FakePlannerModel(_data_decision("Transform the active dataset."))
    frame = SessionFrame(objective=Objective(text="Prepare data for analysis."))

    output = asyncio.run(
        _planner(model, dispatcher).run("Transform the data.", session_frame=frame)
    )

    task = output.session_frame.tasks[-1]
    assert task.status is TaskStatus.FAILED
    assert output.work_outcome is not None
    assert output.work_outcome.status is status
    assert output.work_outcome.blockers == [
        f"Fake dispatcher {status.value} the requested work."
    ]
    assert output.session_frame.evidences == ()
    assert "No Evidence was created" in output.response


def test_task_outcome_identity_mismatch_fails_closed() -> None:
    dispatcher = FakeDispatcher(
        ExecutionStatus.SUCCEEDED,
        returned_task_id=uuid4(),
    )
    model = FakePlannerModel(_data_decision("Profile the active dataset."))
    frame = SessionFrame(objective=Objective(text="Understand the data."))

    output = asyncio.run(
        _planner(model, dispatcher).run("Profile the data.", session_frame=frame)
    )

    assert output.error is not None
    assert output.error.code is PlannerErrorCode.TASK_OUTCOME_MISMATCH
    task = next(
        task for task in output.session_frame.tasks if task.task_id == output.created_task_ids[0]
    )
    assert task.status is TaskStatus.FAILED
    assert output.session_frame.evidences == ()


def test_data_work_without_objective_returns_blocker_without_creating_task() -> None:
    dispatcher = FakeDispatcher(ExecutionStatus.SUCCEEDED)
    model = FakePlannerModel(_data_decision("Profile the active dataset."))

    output = asyncio.run(_planner(model, dispatcher).run("Profile it."))

    assert output.error is not None
    assert output.error.code is PlannerErrorCode.MISSING_OBJECTIVE
    assert output.created_task_ids == ()
    assert output.session_frame.tasks == ()
    assert dispatcher.requests == []


def test_clear_data_request_can_establish_objective_before_creating_task() -> None:
    dispatcher = FakeDispatcher(ExecutionStatus.SUCCEEDED)
    model = FakePlannerModel(
        _data_decision(
            "Profile the active dataset.",
            Capability.DATA_PROFILING,
            objective_text="Understand the active dataset schema and quality.",
        )
    )

    output = asyncio.run(
        _planner(model, dispatcher).run(
            "Understand this dataset by profiling its schema and quality."
        )
    )

    assert output.session_frame.objective is not None
    assert output.session_frame.objective.text == (
        "Understand the active dataset schema and quality."
    )
    assert len(output.session_frame.tasks) == 1
    assert output.session_frame.tasks[0].status is TaskStatus.COMPLETED


def test_semantic_task_change_creates_new_identity_without_rewriting_existing_task() -> None:
    existing = Task(instruction="Profile the dataset.")
    frame = SessionFrame(
        objective=Objective(text="Understand the dataset."),
        tasks=(existing,),
    )
    dispatcher = FakeDispatcher(ExecutionStatus.SUCCEEDED)
    model = FakePlannerModel(_data_decision("Summarize missingness by column."))

    output = asyncio.run(
        _planner(model, dispatcher).run("Now inspect missingness.", session_frame=frame)
    )

    assert len(output.session_frame.tasks) == 2
    old_task, new_task = output.session_frame.tasks
    assert old_task.task_id == existing.task_id
    assert old_task.instruction == "Profile the dataset."
    assert old_task.status is TaskStatus.PENDING
    assert new_task.task_id != old_task.task_id
    assert new_task.instruction == "Summarize missingness by column."
    assert new_task.status is TaskStatus.COMPLETED


def test_explicit_assumption_addition_uses_successor_state_and_never_dispatches() -> None:
    dispatcher = FakeDispatcher(ExecutionStatus.SUCCEEDED)
    model = FakePlannerModel(PlannerDecision(action=PlannerAction.STATE_SUMMARY))
    frame = SessionFrame(objective=Objective(text="Understand churn."))

    output = asyncio.run(
        _planner(model, dispatcher).run(
            "/assumption Rows represent customers.",
            session_frame=frame,
        )
    )

    assert frame.assumptions == ()
    assert len(output.session_frame.assumptions) == 1
    assert output.session_frame.assumptions[0].text == "Rows represent customers."
    assert output.session_frame.evidences == ()
    assert "not empirical Evidence" in output.response
    assert dispatcher.requests == []
    assert model.decision_inputs == []


def _frame_with_admitted_evidence() -> tuple[SessionFrame, Evidence]:
    objective = Objective(text="Understand dataset size.")
    task = Task(instruction="Count rows.", status=TaskStatus.COMPLETED)
    profile = DataProfile(row_count=42, column_count=0, columns=())
    evidence = Evidence(
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
    return (
        SessionFrame(
            objective=objective,
            tasks=(task,),
            data_profile=profile,
            evidences=(evidence,),
        ),
        evidence,
    )


def test_follow_up_answer_uses_admitted_typed_evidence() -> None:
    frame, evidence = _frame_with_admitted_evidence()
    model = FakePlannerModel(PlannerDecision(action=PlannerAction.ANSWER_FROM_STATE))
    dispatcher = FakeDispatcher(ExecutionStatus.SUCCEEDED)

    output = asyncio.run(
        _planner(model, dispatcher).run(
            "How many rows are in the dataset?",
            session_frame=frame,
        )
    )

    assert output.response == "The admitted Evidence reports 42 rows."
    assert output.session_frame == frame
    assert len(model.answer_inputs) == 1
    answer_input = model.answer_inputs[0]
    assert answer_input.latest_request == "How many rows are in the dataset?"
    assert answer_input.evidences == (evidence,)
    assert "assumptions" not in PlannerAnswerInput.model_fields
    assert dispatcher.requests == []


def test_assumption_only_claim_cannot_support_empirical_answer() -> None:
    assumption = Assumption(text="The dataset has 42 rows.")
    frame = SessionFrame(
        objective=Objective(text="Understand dataset size."),
        assumptions=(assumption,),
    )
    model = FakePlannerModel(PlannerDecision(action=PlannerAction.ANSWER_FROM_STATE))
    dispatcher = FakeDispatcher(ExecutionStatus.SUCCEEDED)

    output = asyncio.run(
        _planner(model, dispatcher).run(
            "How many rows are in the dataset?",
            session_frame=frame,
        )
    )

    assert output.error is not None
    assert output.error.code is PlannerErrorCode.NO_ADMITTED_EVIDENCE
    assert "No admitted Evidence" in output.response
    assert model.answer_inputs == []
    assert dispatcher.requests == []
