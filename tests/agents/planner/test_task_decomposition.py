from __future__ import annotations

import asyncio
from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
from pydantic_ai.messages import ModelMessage

from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.dependencies import PlannerDeps
from cognieda.agents.planner.types import (
    PlannerAction,
    PlannerAnswerInput,
    PlannerDecision,
    PlannerDecisionInput,
    PlannerErrorCode,
    PlannerResponseDraft,
)
from cognieda.application.ports import ModelConfig
from cognieda.execution import (
    Capability,
    ExecutionFailure,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
)
from cognieda.runtime.conversation import ConversationHistory
from cognieda.runtime.planner_context import build_planning_context
from cognieda.schemas.artifacts import (
    Assumption,
    DataProfile,
    Evidence,
    Objective,
    SessionFrame,
    Task,
)
from cognieda.schemas.common import EvidenceProvenance
from cognieda.schemas.enums import TaskKind, TaskStatus


@dataclass
class FakeRunResult:
    output: object

    def new_messages(self) -> list[ModelMessage]:
        return []


class RecordingPlannerAgent:
    def __init__(
        self,
        decision: PlannerDecision,
        *,
        answer: str = "The admitted Evidence reports 42 rows.",
    ) -> None:
        self.decision = decision
        self.answer_text = answer
        self.decision_inputs: list[PlannerDecisionInput] = []
        self.answer_inputs: list[PlannerAnswerInput] = []
        self.message_histories: list[tuple[ModelMessage, ...]] = []

    async def run(self, prompt: str, **kwargs: object) -> FakeRunResult:
        output_type = kwargs["output_type"]
        payload = prompt.split("\n", 1)[1]
        if output_type is PlannerDecision:
            self.decision_inputs.append(PlannerDecisionInput.model_validate_json(payload))
            history = kwargs.get("message_history", ())
            self.message_histories.append(tuple(history))  # type: ignore[arg-type]
            return FakeRunResult(output=self.decision)
        if output_type is PlannerResponseDraft:
            self.answer_inputs.append(PlannerAnswerInput.model_validate_json(payload))
            return FakeRunResult(output=PlannerResponseDraft(text=self.answer_text))
        raise AssertionError(f"Unexpected output type: {output_type}")


class FakeAgentFactory:
    def __init__(self, agent: RecordingPlannerAgent) -> None:
        self.agent = agent

    def create_agent(self, **_: object) -> RecordingPlannerAgent:
        return self.agent

    def reload_tooling(self) -> None:
        pass


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


class RaisingDispatcher:
    def __init__(self) -> None:
        self.requests: list[ExecutionRequest] = []

    async def dispatch(self, request: ExecutionRequest) -> ExecutionResult:
        self.requests.append(request)
        raise RuntimeError("provider unavailable")


def _planner(agent: RecordingPlannerAgent, dispatcher: FakeDispatcher) -> Planner:
    return Planner(
        deps=PlannerDeps(dispatcher=dispatcher),
        agent_factory=FakeAgentFactory(agent),  # type: ignore[arg-type]
        model_config=ModelConfig(provider="openai", model_name="test", api_key="test"),
    )


def _context(frame: SessionFrame | None = None):
    return build_planning_context(frame or SessionFrame(), ConversationHistory())


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
    model = RecordingPlannerAgent(_data_decision(instruction, capability))
    objective = Objective(text="Understand the active dataset.")
    frame = SessionFrame(objective=objective)

    output = asyncio.run(
        _planner(model, dispatcher).run(
            "Do the requested bounded data work.",
            planning_context=_context(frame),
        )
    )

    assert output.selected_capability is capability
    assert output.created_task is not None
    assert len(dispatcher.requests) == 1
    request = dispatcher.requests[0]
    assert request.capability is capability
    assert request.input.task.task_id == output.created_task.task_id
    assert request.input.task.objective_id == objective.objective_id
    assert request.input.task.kind is TaskKind.DATA
    assert request.input.task.instruction == instruction
    assert request.input.task.status is TaskStatus.RUNNING


def test_successful_work_preserves_task_identity_and_completes_without_evidence() -> None:
    instruction = "Summarize missingness by column."
    dispatcher = FakeDispatcher(ExecutionStatus.SUCCEEDED)
    model = RecordingPlannerAgent(_data_decision(instruction))
    frame = SessionFrame(objective=Objective(text="Assess dataset quality."))

    output = asyncio.run(
        _planner(model, dispatcher).run(
            "Check missingness.",
            planning_context=_context(frame),
        )
    )

    task = output.created_task
    assert task is not None
    dispatched_task = dispatcher.requests[0].input.task
    assert task.status is TaskStatus.COMPLETED
    assert (
        task.task_id,
        task.objective_id,
        task.kind,
        task.instruction,
    ) == (
        dispatched_task.task_id,
        dispatched_task.objective_id,
        dispatched_task.kind,
        dispatched_task.instruction,
    )
    assert task.instruction == instruction
    assert output.work_outcome is not None
    assert output.work_outcome.status is ExecutionStatus.SUCCEEDED
    assert len(output.work_outcome.result_digest) == 64
    assert "No Evidence was admitted" in output.response


@pytest.mark.parametrize("status", [ExecutionStatus.FAILED, ExecutionStatus.BLOCKED])
def test_failed_or_blocked_work_fails_task_and_surfaces_blocker_without_evidence(
    status: ExecutionStatus,
) -> None:
    dispatcher = FakeDispatcher(status)
    model = RecordingPlannerAgent(_data_decision("Transform the active dataset."))
    frame = SessionFrame(objective=Objective(text="Prepare data for analysis."))

    output = asyncio.run(
        _planner(model, dispatcher).run(
            "Transform the data.",
            planning_context=_context(frame),
        )
    )

    task = output.created_task
    assert task is not None
    assert task.status is TaskStatus.FAILED
    assert output.work_outcome is not None
    assert output.work_outcome.status is status
    assert output.work_outcome.blockers == [
        f"Fake dispatcher {status.value} the requested work."
    ]
    assert "No Evidence was created" in output.response


def test_task_outcome_identity_mismatch_fails_closed() -> None:
    dispatcher = FakeDispatcher(
        ExecutionStatus.SUCCEEDED,
        returned_task_id=uuid4(),
    )
    model = RecordingPlannerAgent(_data_decision("Profile the active dataset."))
    frame = SessionFrame(objective=Objective(text="Understand the data."))

    output = asyncio.run(
        _planner(model, dispatcher).run(
            "Profile the data.",
            planning_context=_context(frame),
        )
    )

    assert output.error is not None
    assert output.error.code is PlannerErrorCode.TASK_OUTCOME_MISMATCH
    task = output.created_task
    assert task is not None
    assert task.status is TaskStatus.FAILED


def test_dispatcher_exception_returns_the_exact_failed_task_result() -> None:
    dispatcher = RaisingDispatcher()
    model = RecordingPlannerAgent(_data_decision("Profile the active dataset."))
    objective = Objective(text="Understand the data.")

    output = asyncio.run(
        _planner(model, dispatcher).run(
            "Profile the data.",
            planning_context=_context(SessionFrame(objective=objective)),
        )
    )

    assert output.error is not None
    assert output.error.code is PlannerErrorCode.DISPATCH_FAILED
    assert output.created_task is not None
    assert output.created_task.status is TaskStatus.FAILED
    dispatched_task = dispatcher.requests[0].input.task
    assert (
        output.created_task.task_id,
        output.created_task.objective_id,
        output.created_task.kind,
        output.created_task.instruction,
    ) == (
        dispatched_task.task_id,
        dispatched_task.objective_id,
        dispatched_task.kind,
        dispatched_task.instruction,
    )


def test_data_work_without_objective_returns_blocker_without_creating_task() -> None:
    dispatcher = FakeDispatcher(ExecutionStatus.SUCCEEDED)
    model = RecordingPlannerAgent(_data_decision("Profile the active dataset."))

    output = asyncio.run(
        _planner(model, dispatcher).run(
            "Profile it.",
            planning_context=_context(),
        )
    )

    assert output.error is not None
    assert output.error.code is PlannerErrorCode.MISSING_OBJECTIVE
    assert output.created_task is None
    assert dispatcher.requests == []


def test_clear_data_request_can_establish_objective_before_creating_task() -> None:
    dispatcher = FakeDispatcher(ExecutionStatus.SUCCEEDED)
    model = RecordingPlannerAgent(
        _data_decision(
            "Profile the active dataset.",
            Capability.DATA_PROFILING,
            objective_text="Understand the active dataset schema and quality.",
        )
    )

    output = asyncio.run(
        _planner(model, dispatcher).run(
            "Understand this dataset by profiling its schema and quality.",
            planning_context=_context(),
        )
    )

    assert output.created_objective is not None
    assert output.created_objective.text == (
        "Understand the active dataset schema and quality."
    )
    assert output.created_task is not None
    assert output.created_task.status is TaskStatus.COMPLETED


def test_semantic_task_change_creates_new_identity_without_rewriting_existing_task() -> None:
    objective = Objective(text="Understand the dataset.")
    existing = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="Profile the dataset.",
    )
    frame = SessionFrame(
        objective=objective,
        tasks=(existing,),
    )
    dispatcher = FakeDispatcher(ExecutionStatus.SUCCEEDED)
    model = RecordingPlannerAgent(_data_decision("Summarize missingness by column."))

    output = asyncio.run(
        _planner(model, dispatcher).run(
            "Now inspect missingness.",
            planning_context=_context(frame),
        )
    )

    new_task = output.created_task
    assert new_task is not None
    assert frame.tasks == (existing,)
    old_task = frame.tasks[0]
    assert new_task.task_id != old_task.task_id
    assert new_task.objective_id == objective.objective_id
    assert new_task.kind is TaskKind.DATA
    assert new_task.instruction == "Summarize missingness by column."
    assert new_task.status is TaskStatus.COMPLETED


def test_explicit_assumption_addition_uses_successor_state_and_never_dispatches() -> None:
    dispatcher = FakeDispatcher(ExecutionStatus.SUCCEEDED)
    model = RecordingPlannerAgent(PlannerDecision(action=PlannerAction.STATE_SUMMARY))
    frame = SessionFrame(objective=Objective(text="Understand churn."))

    output = asyncio.run(
        _planner(model, dispatcher).run(
            "/assumption Rows represent customers.",
            planning_context=_context(frame),
        )
    )

    assert frame.assumptions == ()
    assert output.created_assumption is not None
    assert output.created_assumption.text == "Rows represent customers."
    assert "not empirical Evidence" in output.response
    assert dispatcher.requests == []
    assert model.decision_inputs == []


def _frame_with_admitted_evidence() -> tuple[SessionFrame, Evidence]:
    objective = Objective(text="Understand dataset size.")
    task = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="Count rows.",
        status=TaskStatus.COMPLETED,
    )
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
    model = RecordingPlannerAgent(PlannerDecision(action=PlannerAction.ANSWER_FROM_STATE))
    dispatcher = FakeDispatcher(ExecutionStatus.SUCCEEDED)

    output = asyncio.run(
        _planner(model, dispatcher).run(
            "How many rows are in the dataset?",
            planning_context=_context(frame),
        )
    )

    assert output.response == "The admitted Evidence reports 42 rows."
    assert output.created_objective is None
    assert output.created_assumption is None
    assert output.created_task is None
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
    model = RecordingPlannerAgent(PlannerDecision(action=PlannerAction.ANSWER_FROM_STATE))
    dispatcher = FakeDispatcher(ExecutionStatus.SUCCEEDED)

    output = asyncio.run(
        _planner(model, dispatcher).run(
            "How many rows are in the dataset?",
            planning_context=_context(frame),
        )
    )

    assert output.error is not None
    assert output.error.code is PlannerErrorCode.NO_ADMITTED_EVIDENCE
    assert "No admitted Evidence" in output.response
    assert model.answer_inputs == []
    assert dispatcher.requests == []
