from __future__ import annotations

import asyncio
from collections.abc import Sequence

import pytest
from pydantic import ValidationError
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
from cognieda.execution import ExecutionRequest
from cognieda.schemas.artifacts import Assumption, Objective, SessionFrame, Task


class NeverDispatcher:
    def __init__(self) -> None:
        self.requests: list[ExecutionRequest] = []

    async def dispatch(self, request: ExecutionRequest):
        self.requests.append(request)
        raise AssertionError("This request must not dispatch executor work.")


class FakePlannerModel:
    def __init__(self, decision: PlannerDecision) -> None:
        self.decision = decision
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
            output=PlannerResponseDraft(text="grounded answer"),
            new_messages=(),
        )


def _planner(model: FakePlannerModel, dispatcher: NeverDispatcher) -> Planner:
    return Planner(
        deps=PlannerDeps(dispatcher=dispatcher),
        planner_model=model,
    )


def test_natural_language_understanding_receives_latest_request_and_typed_state() -> None:
    objective = Objective(text="Understand customer retention.")
    assumption = Assumption(text="Rows represent customers.")
    task = Task(instruction="Profile the active dataset.")
    frame = SessionFrame(objective=objective, assumptions=(assumption,), tasks=(task,))
    model = FakePlannerModel(PlannerDecision(action=PlannerAction.STATE_SUMMARY))
    dispatcher = NeverDispatcher()

    output = asyncio.run(
        _planner(model, dispatcher).run(
            "Summarize the active research state.",
            session_frame=frame,
        )
    )

    assert output.decision is not None
    assert output.decision.action is PlannerAction.STATE_SUMMARY
    assert output.session_frame == frame
    assert len(model.decision_inputs) == 1
    model_input = model.decision_inputs[0]
    assert model_input.latest_request == "Summarize the active research state."
    assert model_input.objective == objective
    assert model_input.assumptions == (assumption,)
    assert model_input.tasks == (task,)
    assert dispatcher.requests == []


def test_explicit_and_natural_language_objective_requests_reach_same_typed_action() -> None:
    natural_model = FakePlannerModel(
        PlannerDecision(
            action=PlannerAction.SET_OR_REFINE_OBJECTIVE,
            objective_text="Understand customer churn.",
        )
    )
    explicit_model = FakePlannerModel(PlannerDecision(action=PlannerAction.STATE_SUMMARY))
    dispatcher = NeverDispatcher()

    natural = asyncio.run(
        _planner(natural_model, dispatcher).run("Investigate customer churn.")
    )
    explicit = asyncio.run(
        _planner(explicit_model, dispatcher).run(
            "/objective Understand customer churn."
        )
    )

    assert natural.decision is not None
    assert explicit.decision is not None
    assert natural.decision.action is PlannerAction.SET_OR_REFINE_OBJECTIVE
    assert explicit.decision.action is PlannerAction.SET_OR_REFINE_OBJECTIVE
    assert natural.session_frame.objective is not None
    assert explicit.session_frame.objective is not None
    assert natural.session_frame.objective.text == explicit.session_frame.objective.text
    assert explicit_model.decision_inputs == []


def test_objective_semantic_refinement_allocates_new_identity_without_mutation() -> None:
    original = Objective(text="Understand churn.")
    frame = SessionFrame(objective=original)
    model = FakePlannerModel(
        PlannerDecision(
            action=PlannerAction.SET_OR_REFINE_OBJECTIVE,
            objective_text="Understand churn drivers.",
        )
    )

    output = asyncio.run(
        _planner(model, NeverDispatcher()).run(
            "Refine the objective to focus on drivers.",
            session_frame=frame,
        )
    )

    assert output.session_frame is not frame
    assert output.session_frame.objective is not None
    assert output.session_frame.objective.objective_id != original.objective_id
    assert output.session_frame.objective.text == "Understand churn drivers."
    assert original.text == "Understand churn."


def test_unknown_explicit_command_fails_without_model_fallback_or_state_change() -> None:
    frame = SessionFrame(objective=Objective(text="Keep this Objective."))
    model = FakePlannerModel(PlannerDecision(action=PlannerAction.STATE_SUMMARY))
    dispatcher = NeverDispatcher()

    output = asyncio.run(
        _planner(model, dispatcher).run(
            "/unknown remove everything",
            session_frame=frame,
        )
    )

    assert output.error is not None
    assert output.error.code is PlannerErrorCode.INVALID_COMMAND
    assert output.session_frame == frame
    assert output.created_task_ids == ()
    assert model.decision_inputs == []
    assert dispatcher.requests == []


def test_planner_decision_rejects_untyped_or_mixed_core_changes() -> None:
    with pytest.raises(ValidationError):
        PlannerDecision.model_validate(
            {
                "action": PlannerAction.CREATE_OR_RUN_DATA_TASK,
                "task_instruction": "Profile the dataset.",
                "capability": "not_a_capability",
            }
        )

    with pytest.raises(ValidationError):
        PlannerDecision(
            action=PlannerAction.ADD_ASSUMPTION,
            assumption_text="Rows are customers.",
            task_instruction="Profile the dataset.",
        )
