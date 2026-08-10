from __future__ import annotations

import asyncio
import inspect
import unicodedata
from collections.abc import Sequence

import pytest
from pydantic import ValidationError
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
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
from cognieda.runtime.conversation import ConversationHistory, ConversationSegment
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
        messages = (
            ModelRequest(parts=[UserPromptPart(content=model_input.latest_request)]),
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
        deps=PlannerDeps(dispatcher=dispatcher, research_state=research_state),
        planner_model=model,
    )
    application = Application(
        workspace=object(),  # type: ignore[arg-type]
        planner_agent=planner,
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

    asyncio.run(application.submit_message("Investigate customer churn."))
    first_session = application.session
    asyncio.run(application.submit_message("Summarize what we established."))

    assert application.session is not first_session
    assert application.session.session_id == first_session.session_id
    assert application.session.session_frame.active_objective_id is not None
    objective = research_state.get_objective(
        application.session.session_frame.active_objective_id
    )
    assert objective is not None
    assert objective.text == "Understand customer churn."
    assert model.decision_inputs[1].objective == objective
    assert model.message_histories[0] == ()
    assert model.message_histories[1] == first_session.conversation_history.model_messages()
    assert len(application.session.conversation_history.turns) == 2
    assert application.session.conversation_history.presentation_transcript() == (
        (
            "Investigate customer churn.",
            "Active Objective set to: Understand customer churn.",
        ),
        (
            "Summarize what we established.",
            "Active Objective: Understand customer churn.. Objectives in session history: 1. "
            "Planning Assumptions in session history (not Evidence): 0. "
            "Tasks in session history: 0. DataProfiles in session history: 0. "
            "Evidence items in session history: 0.",
        ),
    )


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
    assert "No admitted Evidence" in response.content
    assert model.answer_inputs == []


def test_evidence_resolves_for_answer_but_conversation_is_not_empirical_input(
    db_session,
) -> None:
    frame, evidence, research_state = _frame_with_admitted_evidence(db_session)
    history = ConversationHistory().add_turn(
        human_message="I think there are 100 rows.",
        planner_response="That is not admitted Evidence.",
        message_segments=((
            ModelRequest(parts=[UserPromptPart(content="I think there are 100 rows.")]),
            ModelResponse(parts=[TextPart(content="That is not admitted Evidence.")]),
        ),),
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
        human_message="First",
        planner_response="First response",
        segments=(
            ConversationSegment(
                messages=(
                    ModelRequest(parts=[UserPromptPart(content="First")]),
                    ModelResponse(parts=[TextPart(content="First response")]),
                )
            ),
        ),
    )
    final = successor.advance(
        session_frame=successor.session_frame,
        human_message="/summary",
        planner_response="Second response",
        segments=(),
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
        human_message="Inspect the active state.",
        planner_response="The active state is ready.",
        message_segments=(messages,),
    )

    restored = ConversationHistory.model_validate_json(history.model_dump_json())

    assert restored.model_messages() == messages
    assert ModelMessagesTypeAdapter.validate_json(
        ModelMessagesTypeAdapter.dump_json(list(restored.model_messages()))
    ) == list(messages)
    assert len(restored.turns) == 1
    assert len(restored.turns[0].segments) == 1


def test_deterministic_turn_retains_surface_without_fake_model_messages() -> None:
    history = ConversationHistory().add_turn(
        human_message="/summary",
        planner_response="No active Objective.",
    )

    assert history.presentation_transcript() == (("/summary", "No active Objective."),)
    assert history.turns[0].segments == ()
    assert history.model_messages() == ()


def test_deterministic_surface_turn_reaches_request_understanding_only_as_discourse(
    db_session,
) -> None:
    history = ConversationHistory().add_turn(
        human_message="/summary",
        planner_response="Task T7 completed with two limitations.",
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

    assert tuple(
        turn.model_dump() for turn in model.decision_inputs[0].surface_discourse
    ) == (
        {
            "human_message": "/summary",
            "planner_response": "Task T7 completed with two limitations.",
        },
    )
    assert model.message_histories == [()]
    assert model.answer_inputs == []
    assert "No admitted Evidence" in response.content
    assert history.turns[0].segments == ()
    assert history.model_messages() == ()
    assert "surface_discourse" not in PlannerAnswerInput.model_fields


def test_context_selection_omits_and_later_reselects_only_whole_segments() -> None:
    history = ConversationHistory()
    segments: list[ConversationSegment] = []
    for index, topic in enumerate(("churn", "pricing", "quality", "schema", "rows", "summary")):
        messages: tuple[ModelMessage, ...] = (
            ModelRequest(parts=[UserPromptPart(content=f"Discuss {topic}")]),
            ModelResponse(parts=[TextPart(content=f"Recorded {topic} turn {index}")]),
        )
        history = history.add_turn(
            human_message=f"Discuss {topic}",
            planner_response=f"Recorded {topic} turn {index}",
            message_segments=(messages,),
        )
        segments.append(history.turns[-1].segments[0])

    current = history.select_for_request_understanding("Continue the current summary")
    later = history.select_for_request_understanding("Return to the churn discussion")

    assert segments[0] not in current.model_segments
    assert tuple(segment.segment_id for segment in current.model_segments) == tuple(
        segment.segment_id for segment in segments[-4:]
    )
    assert segments[0] in later.model_segments
    assert history.turns[0].segments == (segments[0],)
    assert later.model_messages()[0:2] == (*segments[0].messages,)


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
        human_message="Phân tích nhóm khách hàng đã rời bỏ.",
        planner_response="Đã ghi nhận phân tích khách hàng rời bỏ.",
        message_segments=(old_messages,),
    )
    for topic in ("pricing", "quality", "schema", "rows", "summary"):
        history = history.add_turn(
            human_message=f"Discuss {topic}",
            planner_response=f"Recorded {topic}",
        )

    unrelated = history.select_for_request_understanding("Continue with pricing")
    request = "Quay lại phân tích KHÁCH HÀNG rời bỏ."
    selected = history.select_for_request_understanding(request)
    selected_again = history.select_for_request_understanding(request)

    assert history.turns[0] not in unrelated.surface_turns
    assert history.turns[0] in selected.surface_turns
    assert history.turns[0].segments[0] in selected.model_segments
    assert selected == selected_again
    assert history.turns[0].segments[0].messages == old_messages

    decomposed = unicodedata.normalize("NFD", "PHÂN TÍCH KHÁCH HÀNG RỜI BỎ")
    assert ConversationHistory._selection_terms(decomposed) == {
        "phân",
        "tích",
        "khách",
        "hàng",
        "rời",
    }


def test_conversation_segment_rejects_split_tool_protocol() -> None:
    with pytest.raises(ValidationError, match="tool-call/tool-return"):
        ConversationSegment(
            messages=(
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
        )
