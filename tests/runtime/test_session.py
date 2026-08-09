from __future__ import annotations

import asyncio
import inspect
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
from cognieda.runtime.conversation import ConversationHistory
from cognieda.runtime.session import Session
from cognieda.schemas.artifacts import (
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
        objective_id=objective.objective_id,
        task_ids=(task.task_id,),
        data_profile_id=profile.data_profile_id,
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
    assert application.session.session_frame.objective_id is not None
    objective = research_state.get_objective(application.session.session_frame.objective_id)
    assert objective is not None
    assert objective.text == "Understand customer churn."
    assert model.decision_inputs[1].objective == objective
    assert model.message_histories[0] == ()
    assert model.message_histories[1] == first_session.conversation_history.model_messages()
    assert len(application.session.conversation_history.turns) == 2


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
    session = Session(session_frame=SessionFrame(objective_id=objective.objective_id))
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
        (
            ModelRequest(parts=[UserPromptPart(content="I think there are 100 rows.")]),
            ModelResponse(parts=[TextPart(content="That is not admitted Evidence.")]),
        )
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
        messages=(ModelRequest(parts=[UserPromptPart(content="First")]),),
    )
    final = successor.advance(
        session_frame=successor.session_frame,
        messages=(ModelResponse(parts=[TextPart(content="Second response")]),),
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
    history = ConversationHistory().add_turn(messages)

    restored = ConversationHistory.model_validate_json(history.model_dump_json())

    assert restored.model_messages() == messages
    assert ModelMessagesTypeAdapter.validate_json(
        ModelMessagesTypeAdapter.dump_json(list(restored.model_messages()))
    ) == list(messages)
    assert len(restored.turns) == 1
