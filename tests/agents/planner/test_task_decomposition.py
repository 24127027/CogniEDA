from __future__ import annotations

import asyncio
from collections.abc import Sequence

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
from cognieda.execution import Capability, ExecutionRequest
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


class FakePlannerModel:
    def __init__(
        self,
        decision: PlannerDecision,
        *,
        answer: str = "The admitted Evidence reports 42 rows.",
    ) -> None:
        self.decision = decision
        self.answer_text = answer
        self.answer_inputs: list[PlannerAnswerInput] = []

    async def decide(
        self,
        model_input: PlannerModelInput,
        *,
        message_history: Sequence[ModelMessage] = (),
    ) -> PlannerModelResult[PlannerDecision]:
        del model_input, message_history
        return PlannerModelResult(output=self.decision, new_messages=())

    async def answer(
        self, answer_input: PlannerAnswerInput
    ) -> PlannerModelResult[PlannerResponseDraft]:
        self.answer_inputs.append(answer_input)
        return PlannerModelResult(
            output=PlannerResponseDraft(text=self.answer_text),
            new_messages=(),
        )


class NeverDispatcher:
    def __init__(self) -> None:
        self.requests: list[ExecutionRequest] = []

    async def dispatch(self, request: ExecutionRequest):
        self.requests.append(request)
        raise AssertionError("A transient plan must not dispatch before Human approval.")


def _planner(model: FakePlannerModel, dispatcher: NeverDispatcher) -> Planner:
    return Planner(
        deps=PlannerDeps(dispatcher=dispatcher),
        planner_model=model,
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
def test_typed_data_request_proposes_exact_canonical_objects_without_dispatch(
    instruction: str,
    capability: Capability,
) -> None:
    dispatcher = NeverDispatcher()
    objective = Objective(text="Understand the active dataset.")
    output = asyncio.run(
        _planner(FakePlannerModel(_data_decision(instruction, capability)), dispatcher).run(
            "Do the requested bounded data work.",
            planning_context=_context(SessionFrame(objective=objective)),
        )
    )

    assert output.proposed_objective == objective
    assert len(output.proposed_tasks) == 1
    task = output.proposed_tasks[0]
    assert task.kind is TaskKind.DATA
    assert task.instruction == instruction
    revision = output.proposed_plan_revision
    assert revision is not None
    assert revision.task_ids == {task.task_id}
    assert revision.task_bindings[0].required_capability is capability
    assert revision.task_bindings[0].order_rank == 0
    assert str(revision.plan_revision_id) in output.response
    assert "No authoritative state or execution exists yet" in output.response
    assert dispatcher.requests == []


def test_clear_data_request_proposes_objective_and_task_in_one_draft() -> None:
    dispatcher = NeverDispatcher()
    output = asyncio.run(
        _planner(
            FakePlannerModel(
                _data_decision(
                    "Profile the active dataset.",
                    Capability.DATA_PROFILING,
                    objective_text="Understand the active dataset schema and quality.",
                )
            ),
            dispatcher,
        ).run(
            "Understand this dataset by profiling its schema and quality.",
            planning_context=_context(),
        )
    )

    assert output.created_objective is None
    assert output.proposed_objective is not None
    assert output.proposed_objective.text == (
        "Understand the active dataset schema and quality."
    )
    assert dispatcher.requests == []


def test_data_work_without_objective_proposal_is_blocked() -> None:
    dispatcher = NeverDispatcher()
    output = asyncio.run(
        _planner(
            FakePlannerModel(_data_decision("Profile the active dataset.")),
            dispatcher,
        ).run("Profile it.", planning_context=_context())
    )

    assert output.error is not None
    assert output.error.code is PlannerErrorCode.MISSING_OBJECTIVE
    assert output.proposed_plan_revision is None
    assert dispatcher.requests == []


def test_semantic_task_change_proposes_new_identity_without_rewriting_existing_task() -> None:
    objective = Objective(text="Understand the dataset.")
    existing = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="Profile the dataset.",
    )
    frame = SessionFrame(objective=objective, tasks=(existing,))
    dispatcher = NeverDispatcher()

    output = asyncio.run(
        _planner(
            FakePlannerModel(_data_decision("Summarize missingness by column.")),
            dispatcher,
        ).run("Now inspect missingness.", planning_context=_context(frame))
    )

    assert output.proposed_plan_revision is not None
    assert output.proposed_tasks[0].task_id != existing.task_id
    assert frame.tasks == (existing,)
    assert dispatcher.requests == []


def test_explicit_assumption_addition_uses_successor_state_and_never_dispatches() -> None:
    dispatcher = NeverDispatcher()
    frame = SessionFrame(objective=Objective(text="Understand churn."))
    output = asyncio.run(
        _planner(
            FakePlannerModel(PlannerDecision(action=PlannerAction.STATE_SUMMARY)),
            dispatcher,
        ).run(
            "/assumption Rows represent customers.",
            planning_context=_context(frame),
        )
    )

    assert frame.assumptions == ()
    assert output.created_assumption is not None
    assert output.created_assumption.text == "Rows represent customers."
    assert "not empirical Evidence" in output.response
    assert output.proposed_plan_revision is None
    assert dispatcher.requests == []


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
    model = FakePlannerModel(PlannerDecision(action=PlannerAction.ANSWER_FROM_STATE))
    dispatcher = NeverDispatcher()

    output = asyncio.run(
        _planner(model, dispatcher).run(
            "How many rows are in the dataset?",
            planning_context=_context(frame),
        )
    )

    assert output.response == "The admitted Evidence reports 42 rows."
    assert output.proposed_plan_revision is None
    assert model.answer_inputs[0].evidences == (evidence,)
    assert "assumptions" not in PlannerAnswerInput.model_fields
    assert dispatcher.requests == []


def test_assumption_only_claim_cannot_support_empirical_answer() -> None:
    frame = SessionFrame(
        objective=Objective(text="Understand dataset size."),
        assumptions=(Assumption(text="The dataset has 42 rows."),),
    )
    model = FakePlannerModel(PlannerDecision(action=PlannerAction.ANSWER_FROM_STATE))

    output = asyncio.run(
        _planner(model, NeverDispatcher()).run(
            "How many rows are in the dataset?",
            planning_context=_context(frame),
        )
    )

    assert output.error is not None
    assert output.error.code is PlannerErrorCode.NO_ADMITTED_EVIDENCE
    assert model.answer_inputs == []
