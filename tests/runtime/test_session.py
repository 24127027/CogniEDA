from __future__ import annotations

import asyncio
import inspect
import unicodedata
from uuid import uuid4

import pytest
from pydantic import ValidationError
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
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
from cognieda.execution import (
    Capability,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
)
from cognieda.infrastructure.persistence import SqlitePlannerResearchState
from cognieda.infrastructure.persistence.repositories import (
    DataProfileRepository,
    EvidenceRepository,
)
from cognieda.runtime.application import Application
from cognieda.runtime.conversation import (
    APPLICATION_MESSAGE_ORIGIN,
    APPLICATION_MESSAGE_ORIGIN_KEY,
    ConversationHistory,
    _selection_terms,
    complete_turn_messages,
    conversation_response_text,
    conversation_user_text,
    prepare_effective_message_history,
    select_conversation_context,
)
from cognieda.runtime.planner_context import PlannerContextPreparer, select_planner_context
from cognieda.runtime.session import Session
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


class SequencePlannerModel:
    def __init__(self, *decisions: PlannerDecision) -> None:
        self._decisions = iter(decisions)
        self.decision_inputs: list[PlannerModelInput] = []
        self.answer_inputs: list[PlannerAnswerInput] = []
        self.message_histories: list[tuple[ModelMessage, ...]] = []

    async def decide(
        self,
        model_input: PlannerModelInput,
        *,
        message_history: tuple[ModelMessage, ...] = (),
    ) -> PlannerModelResult[PlannerDecision]:
        self.decision_inputs.append(model_input)
        self.message_histories.append(message_history)
        messages = (
            ModelRequest(
                parts=[UserPromptPart(content=model_input.latest_request)],
                instructions=f"Current typed input:\n{model_input.model_dump_json()}",
            ),
            ModelResponse(parts=[TextPart(content="typed decision")]),
        )
        return PlannerModelResult(output=next(self._decisions), new_messages=messages)

    async def answer(
        self, answer_input: PlannerAnswerInput
    ) -> PlannerModelResult[PlannerResponseDraft]:
        self.answer_inputs.append(answer_input)
        messages = (
            ModelRequest(parts=[UserPromptPart(content=answer_input.latest_request)]),
            ModelResponse(parts=[TextPart(content="The admitted Evidence reports 42 rows.")]),
        )
        return PlannerModelResult(
            output=PlannerResponseDraft(text="The admitted Evidence reports 42 rows."),
            new_messages=messages,
        )


class FakeDispatcher:
    def __init__(self) -> None:
        self.requests: list[ExecutionRequest] = []

    async def dispatch(self, request: ExecutionRequest) -> ExecutionResult:
        self.requests.append(request)
        return ExecutionResult(
            source_role="fake_data_explorer",
            task_id=request.input.task.task_id,
            work_id=f"work:{request.input.task.task_id}",
            status=ExecutionStatus.SUCCEEDED,
            limitations=["Evidence admission is application-owned."],
        )


def _application(
    model: SequencePlannerModel,
    research_state: SqlitePlannerResearchState,
    *,
    session: Session | None = None,
) -> tuple[Application, FakeDispatcher]:
    dispatcher = FakeDispatcher()
    planner = Planner(
        deps=PlannerDeps(dispatcher=dispatcher, state_mutations=research_state),
        planner_model=model,
    )
    application = Application(
        workspace=object(),  # type: ignore[arg-type]
        planner_agent=planner,
        planner_context_preparer=PlannerContextPreparer(research_state),
        dispatcher=dispatcher,  # type: ignore[arg-type]
        session=session,
    )
    return application, dispatcher


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


def test_application_retains_ids_and_resolved_context_across_turns(db_session) -> None:
    research_state = SqlitePlannerResearchState(db_session)
    model = SequencePlannerModel(
        PlannerDecision(
            action=PlannerAction.SET_OR_REFINE_OBJECTIVE,
            objective_text="Understand customer churn.",
        ),
        PlannerDecision(action=PlannerAction.STATE_SUMMARY),
    )
    application, _ = _application(model, research_state)
    retained_planner = application.planner_agent

    asyncio.run(application.submit_message("Investigate customer churn."))
    first_session = application.session
    asyncio.run(application.submit_message("Summarize what we established."))

    assert application.session is not first_session
    assert application.planner_agent is retained_planner
    assert application.session.session_id == first_session.session_id
    assert application.session.session_frame.active_objective_id is not None
    objective = research_state.get_objective(
        application.session.session_frame.active_objective_id
    )
    assert objective is not None
    assert objective.text == "Understand customer churn."
    assert model.decision_inputs[1].objective == objective
    assert model.message_histories[1] == prepare_effective_message_history(
        first_session.conversation_history.turns
    )
    assert len(first_session.conversation_history.model_messages()) == 3
    assert "message_history" not in type(
        PlannerContextPreparer(research_state).build(
            latest_request="Inspect fields",
            selection=select_planner_context(first_session.session_frame),
        )
    ).model_fields
    assert len(application.session.conversation_history.turns) == 2
    assert "planning_context" not in Session.model_fields
    assert tuple(
        (conversation_user_text(turn), conversation_response_text(turn))
        for turn in application.session.conversation_history.turns
    ) == (
        ("Investigate customer churn.", "Active Objective set to: Understand customer churn."),
        (
            "Summarize what we established.",
            "Active Objective: Understand customer churn.. Objectives in session history: 1. "
            "Planning Assumptions in session history (not Evidence): 0. "
            "Tasks in session history: 0. DataProfiles in session history: 0. "
            "Evidence items in session history: 0.",
        ),
    )


def test_three_turns_replay_selected_native_history_without_stale_instructions(
    db_session,
) -> None:
    research_state = SqlitePlannerResearchState(db_session)
    model = SequencePlannerModel(
        PlannerDecision(
            action=PlannerAction.SET_OR_REFINE_OBJECTIVE,
            objective_text="Understand customer churn.",
        ),
        PlannerDecision(action=PlannerAction.STATE_SUMMARY),
        PlannerDecision(action=PlannerAction.STATE_SUMMARY),
    )
    application, _ = _application(model, research_state)

    asyncio.run(application.submit_message("Investigate customer churn."))
    asyncio.run(application.submit_message("What did we establish?"))
    before_third_turn = application.session
    asyncio.run(application.submit_message("Summarize that again."))

    retained_native_history = before_third_turn.conversation_history.model_messages()
    assert len(model.message_histories[2]) == len(retained_native_history)
    assert model.message_histories[2] == prepare_effective_message_history(
        before_third_turn.conversation_history.turns
    )
    assert any(
        isinstance(message, ModelRequest) and message.instructions is not None
        for message in retained_native_history
    )
    assert all(
        not isinstance(message, ModelRequest) or message.instructions is None
        for message in model.message_histories[2]
    )
    assert not hasattr(ConversationHistory, "select_for_request_understanding")


def test_current_authoritative_context_wins_over_stale_retained_instructions(
    db_session,
) -> None:
    research_state = SqlitePlannerResearchState(db_session)
    old_objective = research_state.create_objective(Objective(text="Old objective."))
    current_objective = research_state.create_objective(Objective(text="Current objective."))
    old_task = research_state.create_task(
        Task(instruction="Old count.", status=TaskStatus.COMPLETED)
    )
    current_task = research_state.create_task(
        Task(instruction="Current count.", status=TaskStatus.COMPLETED)
    )
    old_profile = DataProfileRepository(db_session).create(
        DataProfile(row_count=10, column_count=0, columns=())
    )
    current_profile = DataProfileRepository(db_session).create(
        DataProfile(row_count=42, column_count=0, columns=())
    )
    old_evidence = EvidenceRepository(db_session).create(
        Evidence(
            task_id=old_task.task_id,
            data_profile_id=old_profile.data_profile_id,
            content={"row_count": 10},
            provenance=EvidenceProvenance(
                producer_role="data_explorer",
                work_reference="work:old",
                dataset_reference="dataset:old",
                data_profile_id=old_profile.data_profile_id,
            ),
        )
    )
    current_evidence = EvidenceRepository(db_session).create(
        Evidence(
            task_id=current_task.task_id,
            data_profile_id=current_profile.data_profile_id,
            content={"row_count": 42},
            provenance=EvidenceProvenance(
                producer_role="data_explorer",
                work_reference="work:current",
                dataset_reference="dataset:current",
                data_profile_id=current_profile.data_profile_id,
            ),
        )
    )
    stale_instructions = (
        f"objective={old_objective.objective_id};"
        f"data_profile={old_profile.data_profile_id};evidence={old_evidence.evidence_id}"
    )
    history = ConversationHistory().add_turn(
        messages=(
            ModelRequest(
                parts=[UserPromptPart(content="Summarize the old state.")],
                instructions=stale_instructions,
            ),
            ModelResponse(parts=[TextPart(content="Old state summarized.")]),
        )
    )
    frame = SessionFrame(
        objective_ids=(old_objective.objective_id, current_objective.objective_id),
        active_objective_id=current_objective.objective_id,
        task_ids=(old_task.task_id, current_task.task_id),
        data_profile_ids=(old_profile.data_profile_id, current_profile.data_profile_id),
        active_data_profile_id=current_profile.data_profile_id,
        evidence_ids=(old_evidence.evidence_id, current_evidence.evidence_id),
    )
    model = SequencePlannerModel(PlannerDecision(action=PlannerAction.STATE_SUMMARY))
    application, _ = _application(
        model,
        research_state,
        session=Session(session_frame=frame, conversation_history=history),
    )

    asyncio.run(application.submit_message("Summarize the current state."))

    model_input = model.decision_inputs[0]
    assert model_input.objective == current_objective
    assert model_input.data_profile == current_profile
    assert model_input.evidences == (current_evidence,)
    assert old_evidence not in model_input.evidences
    replayed_request = model.message_histories[0][0]
    assert isinstance(replayed_request, ModelRequest)
    assert replayed_request.instructions is None
    stored_request = history.turns[0].messages[0]
    assert isinstance(stored_request, ModelRequest)
    assert stored_request.instructions == stale_instructions
    assert application.session.session_frame == frame


def test_application_fails_closed_before_planner_on_dangling_session_reference(
    db_session,
) -> None:
    missing_id = uuid4()
    frame = SessionFrame(
        objective_ids=(missing_id,),
        active_objective_id=missing_id,
    )
    model = SequencePlannerModel(PlannerDecision(action=PlannerAction.STATE_SUMMARY))
    application, _ = _application(
        model,
        SqlitePlannerResearchState(db_session),
        session=Session(session_frame=frame),
    )

    response = asyncio.run(application.submit_message("Summarize state."))

    assert "context resolution failed closed" in response.content
    assert application.session.session_frame == frame
    assert len(application.session.conversation_history.turns) == 1
    assert model.decision_inputs == []


def test_state_summary_reports_cumulative_history_and_active_objective(db_session) -> None:
    research_state = SqlitePlannerResearchState(db_session)
    objective_one = research_state.create_objective(Objective(text="Understand churn."))
    objective_two = research_state.create_objective(
        Objective(text="Understand churn limitations.")
    )
    assumption = research_state.create_assumption(
        Assumption(text="Rows represent customers.")
    )
    tasks = tuple(
        research_state.create_task(
            Task(
                instruction=f"Task {index}",
                status=(TaskStatus.COMPLETED if index < 2 else TaskStatus.PENDING),
            )
        )
        for index in range(25)
    )
    profiles = tuple(
        DataProfileRepository(db_session).create(
            DataProfile(row_count=row_count, column_count=0, columns=())
        )
        for row_count in (10, 20)
    )
    evidences = tuple(
        EvidenceRepository(db_session).create(
            Evidence(
                task_id=tasks[index].task_id,
                data_profile_id=profile.data_profile_id,
                content={"row_count": profile.row_count},
                provenance=EvidenceProvenance(
                    producer_role="data_explorer",
                    work_reference=f"work:count-{index}",
                    dataset_reference=f"dataset:{profile.data_profile_id}",
                    data_profile_id=profile.data_profile_id,
                ),
            )
        )
        for index, profile in enumerate(profiles)
    )
    frame = SessionFrame(
        objective_ids=(objective_one.objective_id, objective_two.objective_id),
        active_objective_id=objective_two.objective_id,
        assumption_ids=(assumption.assumption_id,),
        task_ids=tuple(task.task_id for task in tasks),
        data_profile_ids=tuple(profile.data_profile_id for profile in profiles),
        active_data_profile_id=profiles[1].data_profile_id,
        evidence_ids=tuple(evidence.evidence_id for evidence in evidences),
    )
    model = SequencePlannerModel()
    application, _ = _application(
        model,
        research_state,
        session=Session(session_frame=frame),
    )

    response = asyncio.run(application.submit_message("/summary"))

    assert "Active Objective: Understand churn limitations." in response.content
    assert "Objectives in session history: 2." in response.content
    assert "Planning Assumptions in session history (not Evidence): 1." in response.content
    assert "Tasks in session history: 25." in response.content
    assert "DataProfiles in session history: 2." in response.content
    assert "Evidence items in session history: 2." in response.content
    assert model.decision_inputs == []
    assert application.session.session_frame == frame
    summary_turn = application.session.conversation_history.turns[0]
    assert conversation_user_text(summary_turn) == "/summary"
    assert conversation_response_text(summary_turn) == response.content
    assert len(summary_turn.messages) == 2

    switched_application, _ = _application(
        SequencePlannerModel(),
        research_state,
        session=Session(session_frame=frame.set_active_objective_id(objective_one.objective_id)),
    )
    switched = asyncio.run(switched_application.submit_message("/summary"))

    assert "Active Objective: Understand churn." in switched.content
    assert "Objectives in session history: 2." in switched.content
    assert switched_application.session.session_frame.objective_ids == frame.objective_ids


def test_completed_task_lifecycle_is_resolved_on_the_next_turn(db_session) -> None:
    research_state = SqlitePlannerResearchState(db_session)
    objective = research_state.create_objective(Objective(text="Understand dataset."))
    model = SequencePlannerModel(
        PlannerDecision(
            action=PlannerAction.CREATE_OR_RUN_DATA_TASK,
            task_instruction="Profile the active dataset.",
            capability=Capability.DATA_PROFILING,
        )
    )
    session = Session(
        session_frame=SessionFrame(
            objective_ids=(objective.objective_id,),
            active_objective_id=objective.objective_id,
        )
    )
    application, dispatcher = _application(model, research_state, session=session)

    asyncio.run(application.submit_message("Profile the dataset."))
    task_id = application.session.session_frame.task_ids[0]
    asyncio.run(application.submit_message("/summary"))

    task = research_state.get_task(task_id)
    assert len(dispatcher.requests) == 1
    assert task is not None
    assert task.status is TaskStatus.COMPLETED
    assert application.session.session_frame.task_ids == (task_id,)
    assert model.decision_inputs[0].tasks == ()


def test_assumption_survives_but_cannot_become_empirical_support(db_session) -> None:
    research_state = SqlitePlannerResearchState(db_session)
    model = SequencePlannerModel(PlannerDecision(action=PlannerAction.ANSWER_FROM_STATE))
    application, _ = _application(model, research_state)

    asyncio.run(application.submit_message("/assumption The dataset has 42 rows."))
    response = asyncio.run(application.submit_message("How many rows are there?"))

    assert len(application.session.session_frame.assumption_ids) == 1
    assert application.session.session_frame.evidence_ids == ()
    assert "current bounded context" in response.content
    assert model.answer_inputs == []


def test_evidence_resolves_for_answer_but_conversation_is_not_empirical_input(
    db_session,
) -> None:
    frame, evidence, research_state = _frame_with_admitted_evidence(db_session)
    history = ConversationHistory().add_turn(
        messages=(
            ModelRequest(parts=[UserPromptPart(content="I think there are 100 rows.")]),
            ModelResponse(parts=[TextPart(content="That is not admitted Evidence.")]),
        ),
    )
    model = SequencePlannerModel(PlannerDecision(action=PlannerAction.ANSWER_FROM_STATE))
    application, _ = _application(
        model,
        research_state,
        session=Session(session_frame=frame, conversation_history=history),
    )

    response = asyncio.run(application.submit_message("How many rows are there?"))

    assert response.content == "The admitted Evidence reports 42 rows."
    assert application.session.session_frame == frame
    assert model.answer_inputs[0].evidences == (evidence,)
    assert "conversation" not in PlannerAnswerInput.model_fields
    assert "assumptions" not in PlannerAnswerInput.model_fields


def test_session_components_and_conversation_are_immutable_successors() -> None:
    session = Session()
    successor = session.advance(
        session_frame=session.session_frame,
        messages=(
            ModelRequest(parts=[UserPromptPart(content="First")]),
            ModelResponse(parts=[TextPart(content="First response")]),
        ),
    )
    final = successor.advance(
        session_frame=successor.session_frame,
        messages=complete_turn_messages(
            human_message="/summary",
            planner_response="Second response",
        ),
    )

    assert session.conversation_history.turns == ()
    assert len(final.conversation_history.turns) == 2
    assert final.session_frame is successor.session_frame
    assert "conversation_history" not in SessionFrame.model_fields
    with pytest.raises(ValidationError, match="frozen"):
        final.conversation_history = ConversationHistory()


def test_conversation_contract_contains_provider_messages_only_at_runtime() -> None:
    import cognieda.runtime.conversation as conversation_module
    import cognieda.schemas.artifacts as artifacts_module

    conversation_source = inspect.getsource(conversation_module)
    artifacts_source = inspect.getsource(artifacts_module)

    assert "ModelMessage" in conversation_source
    assert "pydantic_ai" in conversation_source
    assert "ModelMessage" not in artifacts_source
    assert "pydantic_ai" not in artifacts_source
    assert set(ConversationHistory.model_fields) == {"turns"}
    assert set(conversation_module.ConversationTurn.model_fields) == {"turn_id", "messages"}
    assert not hasattr(conversation_module, "ConversationSegment")
    assert not hasattr(ConversationHistory, "presentation_transcript")


def test_completed_turn_keeps_all_internal_native_messages_in_order() -> None:
    native_messages: tuple[ModelMessage, ...] = (
        ModelRequest(parts=[UserPromptPart(content="Inspect the active state.")]),
        ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="lookup_state",
                    args={"scope": "active"},
                    tool_call_id="call-internal",
                )
            ]
        ),
        ModelRequest(
            parts=[
                ToolReturnPart(
                    tool_name="lookup_state",
                    content={"status": "ready"},
                    tool_call_id="call-internal",
                )
            ]
        ),
        ModelResponse(parts=[TextPart(content="Internal typed result")]),
    )

    messages = complete_turn_messages(
        human_message="Inspect the active state.",
        planner_response="The active state is ready.",
        native_messages=native_messages,
    )
    history = ConversationHistory().add_turn(messages=messages)

    assert history.turns[0].messages[: len(native_messages)] == native_messages
    assert len(history.turns[0].messages) == len(native_messages) + 1
    assert conversation_response_text(history.turns[0]) == "The active state is ready."


def test_conversation_round_trip_preserves_tool_call_and_return_coherence() -> None:
    messages: tuple[ModelMessage, ...] = (
        ModelRequest(parts=[UserPromptPart(content="Inspect the active state.")]),
        ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="lookup_state", args={"scope": "active"}, tool_call_id="call-1"
                )
            ]
        ),
        ModelRequest(
            parts=[
                ToolReturnPart(
                    tool_name="lookup_state",
                    content={"status": "ready"},
                    tool_call_id="call-1",
                )
            ]
        ),
        ModelResponse(parts=[TextPart(content="The active state is ready.")]),
    )
    history = ConversationHistory().add_turn(
        messages=messages,
    )

    restored = ConversationHistory.model_validate_json(history.model_dump_json())

    assert restored.model_messages() == messages
    assert ModelMessagesTypeAdapter.validate_json(
        ModelMessagesTypeAdapter.dump_json(list(restored.model_messages()))
    ) == list(messages)
    assert len(restored.turns) == 1
    assert restored.turns[0].messages == messages


def test_conversation_round_trip_preserves_retry_capable_tool_protocol() -> None:
    messages: tuple[ModelMessage, ...] = (
        ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="final_result",
                    args={"row_count": "invalid"},
                    tool_call_id="call-invalid",
                )
            ]
        ),
        ModelRequest(
            parts=[
                RetryPromptPart(
                    content="row_count must be an integer",
                    tool_name="final_result",
                    tool_call_id="call-invalid",
                )
            ]
        ),
        ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="final_result",
                    args={"row_count": 42},
                    tool_call_id="call-valid",
                )
            ]
        ),
        ModelRequest(
            parts=[
                ToolReturnPart(
                    tool_name="final_result",
                    content="Final output processed.",
                    tool_call_id="call-valid",
                )
            ]
        ),
    )
    history = ConversationHistory().add_turn(messages=messages)

    restored = ConversationHistory.model_validate_json(history.model_dump_json())

    assert restored.turns[0].messages == messages
    assert ModelMessagesTypeAdapter.validate_json(
        ModelMessagesTypeAdapter.dump_json(list(restored.model_messages()))
    ) == list(messages)


def test_conversation_turn_does_not_revalidate_native_retry_protocol() -> None:
    messages: tuple[ModelMessage, ...] = (
        ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="final_result",
                    args={"row_count": "invalid"},
                    tool_call_id="call-original",
                )
            ]
        ),
        ModelRequest(
            parts=[
                RetryPromptPart(
                    content="row_count must be an integer",
                    tool_name="final_result",
                    tool_call_id="call-other",
                )
            ]
        ),
    )

    history = ConversationHistory().add_turn(messages=messages)

    assert history.turns[0].messages == messages


def test_deterministic_turn_uses_application_created_native_messages() -> None:
    history = ConversationHistory().add_turn(
        messages=complete_turn_messages(
            human_message="/summary",
            planner_response="No active Objective.",
        ),
    )

    assert conversation_user_text(history.turns[0]) == "/summary"
    assert conversation_response_text(history.turns[0]) == "No active Objective."
    assert len(history.model_messages()) == 2
    request, response = history.model_messages()
    assert request.metadata == {APPLICATION_MESSAGE_ORIGIN_KEY: APPLICATION_MESSAGE_ORIGIN}
    assert response.metadata == {APPLICATION_MESSAGE_ORIGIN_KEY: APPLICATION_MESSAGE_ORIGIN}
    assert isinstance(response, ModelResponse)
    assert response.model_name is None
    assert response.provider_name is None


def test_deterministic_turn_reaches_request_understanding_as_native_history(
    db_session,
) -> None:
    history = ConversationHistory().add_turn(
        messages=complete_turn_messages(
            human_message="/summary",
            planner_response="Task T7 completed with two limitations.",
        ),
    )
    model = SequencePlannerModel(PlannerDecision(action=PlannerAction.ANSWER_FROM_STATE))
    application, _ = _application(
        model,
        SqlitePlannerResearchState(db_session),
        session=Session(conversation_history=history),
    )

    response = asyncio.run(
        application.submit_message("What were the limitations of the task you just mentioned?")
    )

    assert model.message_histories[0] == history.model_messages()
    assert model.answer_inputs == []
    assert "current bounded context" in response.content
    assert len(history.turns[0].messages) == 2
    assert "surface_discourse" not in PlannerAnswerInput.model_fields


def test_context_selection_omits_and_later_reselects_complete_turns() -> None:
    history = ConversationHistory()
    retained_messages: list[tuple[ModelMessage, ...]] = []
    for index, topic in enumerate(("churn", "pricing", "quality", "schema", "rows", "summary")):
        messages: tuple[ModelMessage, ...] = (
            ModelRequest(parts=[UserPromptPart(content=f"Discuss {topic}")]),
            ModelResponse(parts=[TextPart(content=f"Recorded {topic} turn {index}")]),
        )
        history = history.add_turn(messages=messages)
        retained_messages.append(history.turns[-1].messages)

    current = select_conversation_context(history, "Continue the current summary")
    later = select_conversation_context(history, "Return to the churn discussion")

    assert history.turns[0] not in current
    assert current == history.turns[-4:]
    assert history.turns[0] in later
    assert history.turns[0].messages == retained_messages[0]


def test_context_selection_hard_bounds_old_matches_and_preserves_chronology() -> None:
    history = ConversationHistory()
    for index in range(12):
        first_messages: tuple[ModelMessage, ...] = (
            ModelRequest(parts=[UserPromptPart(content=f"Discuss task {index}")]),
            ModelResponse(parts=[TextPart(content=f"Recorded task {index}")]),
        )
        second_messages: tuple[ModelMessage, ...] = (
            ModelRequest(parts=[UserPromptPart(content=f"Clarify task {index}")]),
            ModelResponse(parts=[TextPart(content=f"Clarified task {index}")]),
        )
        history = history.add_turn(
            messages=(*first_messages, *second_messages),
        )
    for index in range(4):
        history = history.add_turn(
            messages=complete_turn_messages(
                human_message=f"Recent topic {index}",
                planner_response=f"Recorded recent topic {index}",
            ),
        )

    selected = select_conversation_context(
        history,
        "What about that task?",
        recent_turn_limit=4,
        older_lexical_match_limit=3,
    )
    selected_again = select_conversation_context(
        history,
        "What about that task?",
        recent_turn_limit=4,
        older_lexical_match_limit=3,
    )
    default_selected = select_conversation_context(history, "What about that task?")

    assert selected == selected_again
    assert selected == (
        *history.turns[9:12],
        *history.turns[12:16],
    )
    assert len(selected) == 7
    assert all(len(turn.messages) == 4 for turn in selected[:3])
    assert history.turns[8] not in selected
    assert len(history.turns) == 16
    assert len(history.turns[8].messages) == 4
    assert default_selected == history.turns[8:16]
    assert len(default_selected) == 8


def test_bounded_evidence_omission_does_not_claim_global_absence(db_session) -> None:
    research_state = SqlitePlannerResearchState(db_session)
    assumption = research_state.create_assumption(
        Assumption(text="The active dataset has 10 rows.")
    )
    active_task = research_state.create_task(
        Task(instruction="Count active rows.", status=TaskStatus.COMPLETED)
    )
    other_task = research_state.create_task(
        Task(instruction="Count other rows.", status=TaskStatus.COMPLETED)
    )
    active_profile = DataProfileRepository(db_session).create(
        DataProfile(row_count=10, column_count=0, columns=())
    )
    other_profile = DataProfileRepository(db_session).create(
        DataProfile(row_count=20, column_count=0, columns=())
    )
    active_evidence = EvidenceRepository(db_session).create(
        Evidence(
            task_id=active_task.task_id,
            data_profile_id=active_profile.data_profile_id,
            content={"row_count": 10},
            provenance=EvidenceProvenance(
                producer_role="data_explorer",
                work_reference="work:active-count",
                dataset_reference="dataset:active",
                data_profile_id=active_profile.data_profile_id,
            ),
        )
    )
    other_evidences = tuple(
        EvidenceRepository(db_session).create(
            Evidence(
                task_id=other_task.task_id,
                data_profile_id=other_profile.data_profile_id,
                content={"row_count": 20, "sequence": index},
                provenance=EvidenceProvenance(
                    producer_role="data_explorer",
                    work_reference=f"work:other-count-{index}",
                    dataset_reference="dataset:other",
                    data_profile_id=other_profile.data_profile_id,
                ),
            )
        )
        for index in range(20)
    )
    frame = SessionFrame(
        assumption_ids=(assumption.assumption_id,),
        task_ids=(active_task.task_id, other_task.task_id),
        data_profile_ids=(active_profile.data_profile_id, other_profile.data_profile_id),
        active_data_profile_id=active_profile.data_profile_id,
        evidence_ids=(
            active_evidence.evidence_id,
            *(evidence.evidence_id for evidence in other_evidences),
        ),
    )
    history = ConversationHistory().add_turn(
        messages=complete_turn_messages(
            human_message="The active dataset has 10 rows.",
            planner_response="That conversation is not admitted Evidence.",
        ),
    )
    model = SequencePlannerModel(PlannerDecision(action=PlannerAction.ANSWER_FROM_STATE))
    application, _ = _application(
        model,
        research_state,
        session=Session(session_frame=frame, conversation_history=history),
    )

    selection = select_planner_context(frame)
    bounded_context = PlannerContextPreparer(research_state).build(
        latest_request="How many rows are in the active dataset?",
        selection=selection,
    )
    response = asyncio.run(
        application.submit_message("How many rows are in the active dataset?")
    )

    assert active_evidence.evidence_id not in selection.evidence_candidate_ids
    assert selection.evidence_candidate_ids == tuple(
        evidence.evidence_id for evidence in other_evidences
    )
    assert bounded_context.data_profile == active_profile
    assert bounded_context.evidences == ()
    assert research_state.get_evidence(active_evidence.evidence_id) == active_evidence
    assert response.content == (
        "No eligible admitted Evidence is available in the current bounded context "
        "to support an empirical answer."
    )
    assert model.answer_inputs == []
    assert application.session.session_frame.evidence_ids == frame.evidence_ids
    assert application.session.conversation_history.turns[0] == history.turns[0]


def test_unicode_selection_normalizes_and_reselects_old_vietnamese_turn() -> None:
    old_messages: tuple[ModelMessage, ...] = (
        ModelRequest(
            parts=[UserPromptPart(content="Phân tích nhóm khách hàng đã rời bỏ.")]
        ),
        ModelResponse(
            parts=[TextPart(content="Đã ghi nhận phân tích khách hàng rời bỏ.")]
        ),
    )
    history = ConversationHistory().add_turn(
        messages=old_messages,
    )
    for topic in ("pricing", "quality", "schema", "rows", "summary"):
        history = history.add_turn(
            messages=complete_turn_messages(
                human_message=f"Discuss {topic}",
                planner_response=f"Recorded {topic}",
            ),
        )

    unrelated = select_conversation_context(history, "Continue with pricing")
    request = "Quay lại phân tích KHÁCH HÀNG rời bỏ."
    selected = select_conversation_context(history, request)
    selected_again = select_conversation_context(history, request)

    assert history.turns[0] not in unrelated
    assert history.turns[0] in selected
    assert selected == selected_again
    assert history.turns[0].messages == old_messages

    decomposed = unicodedata.normalize("NFD", "PHÂN TÍCH KHÁCH HÀNG RỜI BỎ")
    assert _selection_terms(decomposed) == {
        "phân",
        "tích",
        "khách",
        "hàng",
        "rời",
    }


def test_conversation_turn_retains_native_messages_without_protocol_parsing() -> None:
    messages: tuple[ModelMessage, ...] = (
        ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="lookup_state",
                    args={"scope": "active"},
                    tool_call_id="call-split",
                )
            ]
        ),
    )

    history = ConversationHistory().add_turn(messages=messages)

    assert history.turns[0].messages == messages
