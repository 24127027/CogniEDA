from __future__ import annotations

import asyncio
import inspect
from uuid import uuid4

import pytest
from pydantic import ValidationError

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
from cognieda.infrastructure.persistence import SqlitePlannerResearchState
from cognieda.runtime.planner_context import PlannerContextPreparer, select_planner_context
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

    async def decide(
        self,
        model_input: PlannerModelInput,
    ) -> PlannerModelResult[PlannerDecision]:
        self.decision_inputs.append(model_input)
        return PlannerModelResult(output=self.decision, new_messages=())

    async def answer(
        self, answer_input: PlannerAnswerInput
    ) -> PlannerModelResult[PlannerResponseDraft]:
        self.answer_inputs.append(answer_input)
        return PlannerModelResult(
            output=PlannerResponseDraft(text="grounded answer"),
            new_messages=(),
        )


def _planner(
    model: FakePlannerModel,
    dispatcher: NeverDispatcher,
    research_state: SqlitePlannerResearchState,
) -> Planner:
    return Planner(
        deps=PlannerDeps(dispatcher=dispatcher, state_mutations=research_state),
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


def test_natural_language_understanding_receives_latest_materialized_state(db_session) -> None:
    research_state = SqlitePlannerResearchState(db_session)
    objective = research_state.create_objective(Objective(text="Understand retention."))
    assumption = research_state.create_assumption(Assumption(text="Rows are customers."))
    task = research_state.create_task(Task(instruction="Profile the active dataset."))
    frame = SessionFrame(
        objective_ids=(objective.objective_id,),
        active_objective_id=objective.objective_id,
        assumption_ids=(assumption.assumption_id,),
        task_ids=(task.task_id,),
    )
    model = FakePlannerModel(PlannerDecision(action=PlannerAction.STATE_SUMMARY))
    dispatcher = NeverDispatcher()

    output = asyncio.run(
        _planner(model, dispatcher, research_state).run(
            "Summarize the active research state.",
            planning_context=_planning_context(
                research_state, "Summarize the active research state.", frame
            ),
            session_frame=frame,
        )
    )

    assert output.decision is not None
    assert output.decision.action is PlannerAction.STATE_SUMMARY
    assert output.session_frame == frame
    model_input = model.decision_inputs[0]
    assert model_input.latest_request == "Summarize the active research state."
    assert model_input.objective == objective
    assert model_input.assumptions == (assumption,)
    assert model_input.tasks == (task,)
    assert dispatcher.requests == []


def test_planning_context_is_a_distinct_ephemeral_per_run_projection(db_session) -> None:
    research_state = SqlitePlannerResearchState(db_session)
    objective = research_state.create_objective(Objective(text="Understand retention."))
    frame = SessionFrame(
        objective_ids=(objective.objective_id,),
        active_objective_id=objective.objective_id,
    )
    preparer = PlannerContextPreparer(research_state)
    selection = select_planner_context(frame)
    first = preparer.build(latest_request="First request", selection=selection)
    second = preparer.build(latest_request="Second request", selection=selection)

    assert first is not second
    assert first.latest_request == "First request"
    assert second.latest_request == "Second request"
    assert first.objective == objective
    assert "planning_context" not in SessionFrame.model_fields


def test_planner_run_consumes_prepared_context_not_session_conversation_inputs() -> None:
    parameters = inspect.signature(Planner.run).parameters

    assert parameters["planning_context"].default is inspect.Parameter.empty
    assert "surface_discourse" not in parameters
    assert "message_history" not in parameters
    assert "message_history" not in inspect.signature(FakePlannerModel.decide).parameters


def test_explicit_and_natural_objective_requests_reach_same_typed_action(db_session) -> None:
    research_state = SqlitePlannerResearchState(db_session)
    natural_model = FakePlannerModel(
        PlannerDecision(
            action=PlannerAction.SET_OR_REFINE_OBJECTIVE,
            objective_text="Understand customer churn.",
        )
    )
    explicit_model = FakePlannerModel(PlannerDecision(action=PlannerAction.STATE_SUMMARY))
    dispatcher = NeverDispatcher()

    natural = asyncio.run(
        _planner(natural_model, dispatcher, research_state).run(
            "Investigate customer churn.",
            planning_context=_planning_context(
                research_state, "Investigate customer churn."
            ),
        )
    )
    explicit = asyncio.run(
        _planner(explicit_model, dispatcher, research_state).run(
            "/objective Understand customer churn.",
            planning_context=_planning_context(
                research_state, "/objective Understand customer churn."
            ),
        )
    )

    assert natural.decision is not None
    assert explicit.decision is not None
    assert natural.decision.action is PlannerAction.SET_OR_REFINE_OBJECTIVE
    assert explicit.decision.action is PlannerAction.SET_OR_REFINE_OBJECTIVE
    assert natural.session_frame.active_objective_id is not None
    assert explicit.session_frame.active_objective_id is not None
    natural_objective = research_state.get_objective(
        natural.session_frame.active_objective_id
    )
    explicit_objective = research_state.get_objective(
        explicit.session_frame.active_objective_id
    )
    assert natural_objective is not None
    assert explicit_objective is not None
    assert natural_objective.text == explicit_objective.text
    assert explicit_model.decision_inputs == []


def test_objective_semantic_refinement_allocates_new_authoritative_identity(db_session) -> None:
    research_state = SqlitePlannerResearchState(db_session)
    original = research_state.create_objective(Objective(text="Understand churn."))
    frame = SessionFrame(
        objective_ids=(original.objective_id,),
        active_objective_id=original.objective_id,
    )
    model = FakePlannerModel(
        PlannerDecision(
            action=PlannerAction.SET_OR_REFINE_OBJECTIVE,
            objective_text="Understand churn drivers.",
        )
    )

    output = asyncio.run(
        _planner(model, NeverDispatcher(), research_state).run(
            "Refine the objective to focus on drivers.",
            planning_context=_planning_context(
                research_state, "Refine the objective to focus on drivers.", frame
            ),
            session_frame=frame,
        )
    )

    assert output.session_frame is not frame
    assert output.session_frame.objective_ids[0] == original.objective_id
    assert len(output.session_frame.objective_ids) == 2
    assert output.session_frame.active_objective_id != original.objective_id
    assert output.session_frame.active_objective_id is not None
    replacement = research_state.get_objective(output.session_frame.active_objective_id)
    assert replacement is not None
    assert replacement.text == "Understand churn drivers."
    assert research_state.get_objective(original.objective_id) == original


def test_dangling_reference_fails_closed_during_application_context_preparation(
    db_session,
) -> None:
    research_state = SqlitePlannerResearchState(db_session)
    missing_id = uuid4()
    frame = SessionFrame(
        objective_ids=(missing_id,),
        active_objective_id=missing_id,
    )
    model = FakePlannerModel(PlannerDecision(action=PlannerAction.STATE_SUMMARY))

    with pytest.raises(ValueError, match="missing Objective"):
        _planning_context(research_state, "Summarize state.", frame)

    assert model.decision_inputs == []


def test_unknown_explicit_command_fails_without_model_fallback_or_state_change(
    db_session,
) -> None:
    research_state = SqlitePlannerResearchState(db_session)
    objective = research_state.create_objective(Objective(text="Keep this Objective."))
    frame = SessionFrame(
        objective_ids=(objective.objective_id,),
        active_objective_id=objective.objective_id,
    )
    model = FakePlannerModel(PlannerDecision(action=PlannerAction.STATE_SUMMARY))
    dispatcher = NeverDispatcher()

    output = asyncio.run(
        _planner(model, dispatcher, research_state).run(
            "/unknown remove everything",
            planning_context=_planning_context(
                research_state, "/unknown remove everything", frame
            ),
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
