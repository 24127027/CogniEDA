from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import StateSnapshot
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from sqlmodel import Session

from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.context import PlannerContext, PlannerRunContext
from cognieda.agents.planner.dependencies import PlannerToolDeps
from cognieda.agents.planner.graph import InProcessPlannerSerializer, build_graph
from cognieda.agents.planner.state import (
    PlannerState,
    PlannerTurnOutcome,
)
from cognieda.agents.planner.types import (
    PlannerControlledError,
    PlannerErrorCode,
    PlannerOutput,
    PlannerResult,
)
from cognieda.application.ports import AgentFactoryPort
from cognieda.application.services import PlanAdmissionService
from cognieda.delegation import ExecutionRequest, ExecutionResult, ExecutionStatus
from cognieda.infrastructure.persistence.repositories import (
    ActivePlanRepository,
    ObjectiveRepository,
    PlanRepository,
    SessionFrameRepository,
    TaskRepository,
)
from cognieda.runtime.conversation import (
    ConversationHistory,
    ConversationSegment,
)
from cognieda.runtime.planner_context import build_planner_context
from cognieda.schemas import Objective, Plan, SessionFrame, Task, TaskKind


def _messages(request: str, response: str) -> tuple[ModelMessage, ...]:
    return (
        ModelRequest(parts=[UserPromptPart(content=request)]),
        ModelResponse(parts=[TextPart(content=response)]),
    )


class RecordingDispatcher:
    def __init__(self) -> None:
        self.requests: list[ExecutionRequest] = []

    async def dispatch(self, request: ExecutionRequest) -> ExecutionResult:
        self.requests.append(request)
        return ExecutionResult(
            source_role="recording_dispatcher",
            task_id=request.input.task.task_id,
            work_id="recorded",
            status=ExecutionStatus.SUCCEEDED,
        )


class RecordingAdmission:
    def __init__(self, service: PlanAdmissionService) -> None:
        self.service = service
        self.calls: list[Plan] = []

    def admit(self, plan: Plan) -> Plan:
        self.calls.append(plan)
        return self.service.admit(plan)


class SequencePlanner(Planner):
    def __init__(
        self,
        outputs: Iterable[PlannerOutput],
        *,
        plan_admission: PlanAdmissionService | RecordingAdmission,
        dispatcher: RecordingDispatcher | None = None,
        checkpointer: BaseCheckpointSaver[Any] | None = None,
        thread_id: UUID | None = None,
    ) -> None:
        self._outputs = iter(outputs)
        self.requests: list[str] = []
        self.contexts: list[PlannerContext] = []
        self.candidates: list[Plan | None] = []
        self.message_histories: list[tuple[ModelMessage, ...]] = []
        self.recording_dispatcher = dispatcher or RecordingDispatcher()
        super().__init__(
            deps=PlannerToolDeps(dispatcher=self.recording_dispatcher),
            agent_factory=cast(AgentFactoryPort, object()),
            model_config=None,
            plan_admission=plan_admission,
            checkpointer=checkpointer,
            thread_id=thread_id,
        )

    async def _invoke_cognitive(
        self,
        request: str,
        *,
        context: PlannerContext,
        candidate_plan: Plan | None = None,
        message_history: list[ModelMessage] | None = None,
    ) -> PlannerOutput:
        self.requests.append(request)
        self.contexts.append(context)
        self.candidates.append(candidate_plan)
        self.message_histories.append(tuple(message_history or ()))
        return next(self._outputs)


def _candidate_result(
    *,
    objective: Objective | None = None,
    instruction: str = "Profile churn labels.",
    response: str = "I propose a bounded investigation.",
) -> PlannerResult:
    objective = objective or Objective(text="Understand customer churn.")
    task = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction=instruction,
    )
    plan = Plan(objective=objective, tasks=(task,))
    return PlannerResult(plan=plan, response=response)


def _planner(
    outputs: Iterable[PlannerOutput],
    db_session: Session,
    *,
    plan_admission: PlanAdmissionService | RecordingAdmission | None = None,
    dispatcher: RecordingDispatcher | None = None,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
    thread_id: UUID | None = None,
) -> SequencePlanner:
    return SequencePlanner(
        outputs,
        plan_admission=plan_admission or PlanAdmissionService(db_session),
        dispatcher=dispatcher,
        checkpointer=checkpointer,
        thread_id=thread_id,
    )


def _snapshot(planner: Planner) -> StateSnapshot:
    return asyncio.run(planner.graph.aget_state(planner._graph_config))


def _state(planner: Planner) -> PlannerState:
    return cast(PlannerState, _snapshot(planner).values)


def _is_waiting(planner: Planner) -> bool:
    return any(task.interrupts for task in _snapshot(planner).tasks)


def test_graph_state_and_outcome_have_exact_separate_ownership(
    db_session: Session,
) -> None:
    planner = _planner(
        (PlannerOutput(result=PlannerResult(response="Done.")),),
        db_session,
    )

    assert tuple(PlannerState.__annotations__) == (
        "latest_human_input",
        "candidate_plan",
        "turn_outcome",
        "completed_segments",
    )
    assert "completed_segment" not in PlannerState.__annotations__
    assert "messages" not in PlannerState.__annotations__
    assert "context" not in PlannerState.__annotations__
    assert tuple(PlannerTurnOutcome.model_fields) == (
        "proposed_plan",
        "response",
        "human_input_request",
        "error",
    )
    assert set(planner.graph.get_graph().nodes) == {
        "__start__",
        "plan_or_answer",
        "await_human",
        "admit_candidate",
        "__end__",
    }
    assert planner.graph.builder.edges == {
        ("__start__", "plan_or_answer"),
        ("await_human", "plan_or_answer"),
        ("admit_candidate", "__end__"),
    }


def test_candidate_proposal_is_checkpointed_without_authoritative_writes(
    db_session: Session,
) -> None:
    segment = ConversationSegment(messages=_messages("Investigate churn.", "Proposed a plan."))
    candidate = _candidate_result()
    assert candidate.plan is not None
    planner = _planner(
        (PlannerOutput(result=candidate, segment=segment),),
        db_session,
    )

    outcome, completed_segments = asyncio.run(
        planner.handle_message("Investigate churn.", context=PlannerContext())
    )
    state = _state(planner)
    persisted_candidate = state["candidate_plan"]

    assert outcome.proposed_plan == candidate.plan
    assert completed_segments == (segment,)
    assert persisted_candidate == candidate.plan
    assert persisted_candidate is not None
    assert persisted_candidate.tasks == candidate.plan.tasks
    assert "messages" not in state
    assert _is_waiting(planner)
    assert ObjectiveRepository(db_session).get_by_id(candidate.plan.objective.objective_id) is None
    assert TaskRepository(db_session).get_by_id(candidate.plan.tasks[0].task_id) is None
    assert PlanRepository(db_session).get_by_id(candidate.plan.plan_id) is None


def test_empty_human_input_is_rejected_before_interrupt_resume(
    db_session: Session,
) -> None:
    candidate = _candidate_result()
    assert candidate.plan is not None
    first_segment = ConversationSegment(
        messages=_messages("Investigate churn.", "Proposed a plan.")
    )
    planner = _planner(
        (
            PlannerOutput(result=candidate, segment=first_segment),
            PlannerOutput(result=PlannerResult(response="The candidate remains available.")),
        ),
        db_session,
    )

    asyncio.run(planner.handle_message("Investigate churn.", context=PlannerContext()))
    before = _state(planner)
    rejected, _ = asyncio.run(planner.handle_message("  ", context=PlannerContext()))

    assert rejected.error is not None
    assert rejected.error.code is PlannerErrorCode.INVALID_REQUEST
    assert planner.requests == ["Investigate churn."]
    assert _state(planner) == before
    assert _is_waiting(planner)

    resumed, _ = asyncio.run(planner.handle_message("Why this scope?", context=PlannerContext()))
    assert resumed.response == "The candidate remains available."
    assert planner.requests == ["Investigate churn.", "Why this scope?"]


def test_natural_multiturn_review_retain_replace_and_authorize_exact_candidate(
    db_session: Session,
) -> None:
    objective = Objective(text="Understand customer churn.")
    p1 = _candidate_result(objective=objective, instruction="Analyze pricing cohorts.")
    p2 = _candidate_result(objective=objective, instruction="Analyze support cohorts.")
    assert p1.plan is not None and p2.plan is not None
    seg1 = ConversationSegment(messages=_messages("Investigate churn.", "P1"))
    seg_exp = ConversationSegment(messages=_messages("Why is pricing included?", "Explanation"))
    seg2 = ConversationSegment(messages=_messages("Remove pricing.", "P2"))
    seg_auth = ConversationSegment(messages=_messages("That looks right, proceed.", "Authorized"))
    admission = RecordingAdmission(PlanAdmissionService(db_session))
    planner = _planner(
        (
            PlannerOutput(result=p1, segment=seg1),
            PlannerOutput(
                result=PlannerResult(response="Pricing was included as a possible driver."),
                segment=seg_exp,
            ),
            PlannerOutput(result=p2, segment=seg2),
            PlannerOutput(
                result=PlannerResult(continue_execution=True),
                segment=seg_auth,
            ),
        ),
        db_session,
        plan_admission=admission,
    )
    context = PlannerContext(objectives=(objective,))

    first, _ = asyncio.run(planner.handle_message("Investigate churn.", context=context))
    assert first.proposed_plan == p1.plan
    assert _state(planner)["candidate_plan"] == p1.plan

    explanation, _ = asyncio.run(
        planner.handle_message(
            "Why is pricing included?",
            context=context,
            message_history=tuple(seg1.messages),
        )
    )
    assert explanation.proposed_plan is None
    assert _state(planner)["candidate_plan"] == p1.plan
    assert planner.candidates[1] == p1.plan
    assert admission.calls == []

    replacement, _ = asyncio.run(
        planner.handle_message(
            "Remove pricing.",
            context=context,
            message_history=(*seg1.messages, *seg_exp.messages),
        )
    )
    assert replacement.proposed_plan == p2.plan
    assert _state(planner)["candidate_plan"] == p2.plan
    assert admission.calls == []

    outcome, _ = asyncio.run(
        planner.handle_message(
            "That looks right, proceed.",
            context=context,
            message_history=(*seg1.messages, *seg_exp.messages, *seg2.messages),
        )
    )
    assert admission.calls == [p2.plan]
    assert _state(planner)["candidate_plan"] is None
    assert outcome.response == "The proposed Plan was admitted and activated."
    assert ActivePlanRepository(db_session).get_by_objective_id(objective.objective_id) == p2.plan
    assert not _is_waiting(planner)
    assert planner.message_histories == [
        (),
        seg1.messages,
        (*seg1.messages, *seg_exp.messages),
        (*seg1.messages, *seg_exp.messages, *seg2.messages),
    ]


def test_context_is_fresh_and_native_history_derived_from_conversation_history(
    db_session: Session,
) -> None:
    first_messages = _messages("First question.", "First answer.")
    second_messages = _messages("Second question.", "Second answer.")
    seg1 = ConversationSegment(messages=first_messages)
    seg2 = ConversationSegment(messages=second_messages)
    session_frames = SessionFrameRepository(db_session, scope_key="fresh-context")
    planner = _planner(
        (
            PlannerOutput(result=PlannerResult(response="First answer."), segment=seg1),
            PlannerOutput(
                result=PlannerResult(response="Second answer."),
                segment=seg2,
            ),
        ),
        db_session,
    )
    first_objective = Objective(text="First current Objective.")
    second_objective = Objective(text="Second current Objective.")
    session_frames.save_current(SessionFrame(objectives=(first_objective,)))

    history = ConversationHistory()
    context_1 = build_planner_context(session_frames.get_current())
    _, segments_1 = asyncio.run(
        planner.handle_message(
            "First question.",
            context=context_1,
            message_history=tuple(history.model_messages()),
        )
    )
    assert segments_1 == (seg1,)
    history = history.add_turn(segments_1)

    session_frames.save_current(SessionFrame(objectives=(second_objective,)))
    context_2 = build_planner_context(session_frames.get_current())
    _, segments_2 = asyncio.run(
        planner.handle_message(
            "Second question.",
            context=context_2,
            message_history=tuple(history.model_messages()),
        )
    )
    assert segments_2 == (seg2,)

    assert planner.contexts[0].objectives == (first_objective,)
    assert planner.contexts[1].objectives == (second_objective,)
    assert planner.contexts[0] is not planner.contexts[1]
    assert planner.message_histories == [(), first_messages]
    assert "messages" not in _state(planner)
    assert "context" not in PlannerState.__annotations__


def test_segment_pruning_actually_changes_model_context(db_session: Session) -> None:
    """Regression test: truncating ConversationHistory removes messages from next invocation."""
    s1 = ConversationSegment(messages=_messages("Q1", "A1"))
    s2 = ConversationSegment(messages=_messages("Q2", "A2"))
    s3 = ConversationSegment(messages=_messages("Q3", "A3"))

    history = ConversationHistory().commit_segment(s1).commit_segment(s2).commit_segment(s3)

    # 1. Verify full flattened history
    assert history.model_messages() == [*s1.messages, *s2.messages, *s3.messages]

    # 2. Truncate from S2 -> retained becomes [S1]
    truncated_history = history.truncate_from(s2.segment_id)
    assert truncated_history.model_messages() == list(s1.messages)

    # 3. Next cognitive turn receives history derived only from truncated_history
    planner = _planner(
        (PlannerOutput(result=PlannerResult(response="Response to Q4")),),
        db_session,
    )
    asyncio.run(
        planner.handle_message(
            "Q4",
            context=PlannerContext(),
            message_history=tuple(truncated_history.model_messages()),
        )
    )

    assert len(planner.message_histories) == 1
    assert planner.message_histories[0] == s1.messages
    # Must NOT contain messages from S2 or S3
    for msg in (*s2.messages, *s3.messages):
        assert msg not in planner.message_histories[0]


def test_discard_clears_candidate_and_repeat_discard_fails_closed(
    db_session: Session,
) -> None:
    candidate = _candidate_result()
    planner = _planner(
        (
            PlannerOutput(result=candidate),
            PlannerOutput(
                result=PlannerResult(
                    response="I discarded the proposal.",
                    discard_candidate=True,
                )
            ),
            PlannerOutput(result=PlannerResult(discard_candidate=True)),
        ),
        db_session,
    )

    asyncio.run(planner.handle_message("Investigate churn.", context=PlannerContext()))
    discarded, _ = asyncio.run(
        planner.handle_message("Abandon that proposal.", context=PlannerContext())
    )
    assert _state(planner)["candidate_plan"] is None
    assert discarded.response == "I discarded the proposal."
    assert not _is_waiting(planner)

    invalid, _ = asyncio.run(planner.handle_message("Discard it again.", context=PlannerContext()))
    assert invalid.error is not None
    assert invalid.error.code.value == "invalid_lifecycle_state"


def test_admission_failure_retains_exact_candidate_and_reports_controlled_error(
    db_session: Session,
) -> None:
    candidate = _candidate_result()
    assert candidate.plan is not None
    existing = ObjectiveRepository(db_session).create(
        Objective(objective_id=candidate.plan.objective.objective_id, text="Collision")
    )
    assert existing != candidate.plan.objective
    planner = _planner(
        (
            PlannerOutput(result=candidate),
            PlannerOutput(result=PlannerResult(continue_execution=True)),
        ),
        db_session,
    )

    asyncio.run(planner.handle_message("Investigate churn.", context=PlannerContext()))
    outcome, _ = asyncio.run(
        planner.handle_message("Proceed with that exact proposal.", context=PlannerContext())
    )
    persisted_candidate = _state(planner)["candidate_plan"]

    assert persisted_candidate == candidate.plan
    assert persisted_candidate is not None
    assert persisted_candidate.tasks == candidate.plan.tasks
    assert outcome.error is not None
    assert outcome.error.code.value == "plan_admission_failed"
    assert PlanRepository(db_session).get_by_id(candidate.plan.plan_id) is None


@pytest.mark.parametrize(
    "objectives",
    [
        (),
        (Objective(text="Single Objective"),),
        (Objective(text="First Objective"), Objective(text="Second Objective")),
    ],
)
def test_continue_execution_without_candidate_fails_closed_regardless_of_objectives(
    db_session: Session,
    objectives: tuple[Objective, ...],
) -> None:
    context = PlannerContext(objectives=objectives)
    planner = _planner(
        (PlannerOutput(result=PlannerResult(continue_execution=True)),),
        db_session,
    )

    outcome, _ = asyncio.run(planner.handle_message("Continue work.", context=context))

    assert outcome.error is not None
    assert outcome.error.code == PlannerErrorCode.INVALID_LIFECYCLE_STATE
    assert "invalid for the retained lifecycle state" in outcome.error.message


def test_inmemory_checkpointer_isolates_planner_thread_identity(
    db_session: Session,
) -> None:
    first = _candidate_result(instruction="First thread task.")
    second = _candidate_result(instruction="Second thread task.")
    first_planner = _planner(
        (PlannerOutput(result=first),),
        db_session,
        thread_id=uuid4(),
    )
    second_planner = _planner(
        (PlannerOutput(result=second),),
        db_session,
        checkpointer=first_planner._checkpointer,
        thread_id=uuid4(),
    )

    asyncio.run(first_planner.handle_message("First request.", context=PlannerContext()))
    assert _state(first_planner)["candidate_plan"] == first.plan
    assert not _snapshot(second_planner).values

    asyncio.run(second_planner.handle_message("Second request.", context=PlannerContext()))
    assert _state(second_planner)["candidate_plan"] == second.plan
    assert _state(first_planner)["candidate_plan"] == first.plan


def test_interrupt_resume_receives_fresh_context_while_preserving_candidate(
    db_session: Session,
) -> None:
    """Turn 1 interrupts with C1; Turn 2 resumes with C2 and sees C2 in plan_or_answer."""
    objective_1 = Objective(text="Initial objective S1.")
    objective_2 = Objective(text="Changed authoritative objective S2.")
    candidate = _candidate_result(objective=objective_1, instruction="Profile S1 data.")
    assert candidate.plan is not None

    turn1_messages = _messages("Propose plan.", "Here is the proposal.")
    turn2_messages = _messages("Explain why S2 matters.", "Here is the explanation for S2.")
    seg1 = ConversationSegment(messages=turn1_messages)
    seg2 = ConversationSegment(messages=turn2_messages)

    planner = _planner(
        (
            PlannerOutput(result=candidate, segment=seg1),
            PlannerOutput(
                result=PlannerResult(response="Explanation with fresh context."),
                segment=seg2,
            ),
        ),
        db_session,
    )

    # Turn 1: Propose candidate -> awaits human review
    context_1 = PlannerContext(objectives=(objective_1,))
    outcome_1, _ = asyncio.run(planner.handle_message("Propose plan.", context=context_1))
    assert outcome_1.proposed_plan == candidate.plan
    assert _is_waiting(planner)
    assert _state(planner)["candidate_plan"] == candidate.plan
    assert len(planner.contexts) == 1
    assert planner.contexts[0].objectives == (objective_1,)

    # Between turns: authoritative state changes to S2
    context_2 = PlannerContext(objectives=(objective_2,))

    # Turn 2: Human asks a question while candidate is waiting (resumes interrupt)
    outcome_2, _ = asyncio.run(
        planner.handle_message(
            "Explain why S2 matters.",
            context=context_2,
            message_history=tuple(seg1.messages),
        )
    )

    assert outcome_2.response == "Explanation with fresh context."

    # Invariant checks:
    # 1. plan_or_answer in Turn 2 received context_2 (S2)
    assert len(planner.contexts) == 2
    assert planner.contexts[1].objectives == (objective_2,)
    assert planner.contexts[1] is not planner.contexts[0]

    # 2. Retained candidate survives across the interrupt-resume boundary
    assert _state(planner)["candidate_plan"] == candidate.plan
    assert planner.candidates[1] == candidate.plan

    # 3. Model message history passed from conversation memory reaches cognitive invocation
    assert planner.message_histories[1] == turn1_messages


def test_planner_context_is_not_checkpointed(db_session: Session) -> None:
    """Checkpointer must store only lifecycle state, never PlannerContext."""
    objective = Objective(text="Scope verification.")
    planner = _planner(
        (PlannerOutput(result=PlannerResult(response="Done.")),),
        db_session,
    )
    context = PlannerContext(objectives=(objective,))
    asyncio.run(planner.handle_message("Run test.", context=context))

    snapshot = _snapshot(planner)
    values = snapshot.values
    assert isinstance(values, dict)
    assert "context" not in values
    assert "planner_context" not in values
    assert not any(isinstance(v, PlannerContext) for v in values.values())


def test_custom_serializer_is_required_for_nested_typed_plan_state() -> None:
    candidate = _candidate_result()
    assert candidate.plan is not None
    state = {
        "candidate_plan": candidate.plan,
    }

    plain_serializer = InMemorySaver().serde
    planner_serializer = InProcessPlannerSerializer()
    plain = plain_serializer.loads_typed(plain_serializer.dumps_typed(state))
    restored = planner_serializer.loads_typed(planner_serializer.dumps_typed(state))

    assert isinstance(plain["candidate_plan"], Plan)
    # The default JsonPlusSerializer fails to round-trip nested Pydantic models as Task instances
    assert not isinstance(plain["candidate_plan"].tasks[0], Task)
    assert restored == state
    assert isinstance(restored["candidate_plan"].tasks[0], Task)


def test_build_graph_schema_types() -> None:
    """build_graph must declare StateGraph with correct StateT and ContextT."""
    checkpointer = InMemorySaver(serde=InProcessPlannerSerializer())

    async def fake_invoke(request: str, **kwargs: Any) -> PlannerOutput:
        return PlannerOutput(result=PlannerResult(response="ok"))

    class FakeAdmission:
        def admit(self, plan: Plan) -> Plan:
            return plan

    graph = build_graph(
        checkpointer,
        invoke_cognitive=fake_invoke,
        plan_admission=FakeAdmission(),
    )

    builder = graph.builder
    assert builder.state_schema is PlannerState
    assert builder.context_schema is PlannerRunContext
    assert builder.input_schema is PlannerState
    assert builder.output_schema is PlannerState


def test_multi_segment_cognitive_execution_accumulates_ordered_segments() -> None:
    """Exercise sequential cognitive nodes in one Human turn and verify (S1, S2, S3)
    accumulation.
    """
    from functools import partial

    from langgraph.graph import END, START, StateGraph

    from cognieda.agents.planner.nodes import plan_or_answer

    s1 = ConversationSegment(messages=_messages("Step 1", "Resp 1"))
    s2 = ConversationSegment(messages=_messages("Step 2", "Resp 2"))
    s3 = ConversationSegment(messages=_messages("Step 3", "Resp 3"))

    async def invoke_1(request: str, **kwargs: Any) -> PlannerOutput:
        return PlannerOutput(result=PlannerResult(response="R1"), segment=s1)

    async def invoke_2(request: str, **kwargs: Any) -> PlannerOutput:
        return PlannerOutput(result=PlannerResult(response="R2"), segment=s2)

    async def invoke_3(request: str, **kwargs: Any) -> PlannerOutput:
        return PlannerOutput(result=PlannerResult(response="R3"), segment=s3)

    builder = StateGraph(state_schema=PlannerState, context_schema=PlannerRunContext)
    builder.add_node(
        "node1",
        partial(plan_or_answer, invoke_cognitive=invoke_1),
        destinations=("node2",),
    )
    builder.add_node(
        "node2",
        partial(plan_or_answer, invoke_cognitive=invoke_2),
        destinations=("node3",),
    )
    builder.add_node(
        "node3",
        partial(plan_or_answer, invoke_cognitive=invoke_3),
        destinations=(END,),
    )
    builder.add_edge(START, "node1")
    builder.add_edge("node1", "node2")
    builder.add_edge("node2", "node3")
    builder.add_edge("node3", END)
    graph = builder.compile()

    run_context = PlannerRunContext(planner_context=PlannerContext())
    result = asyncio.run(
        graph.ainvoke(
            {"latest_human_input": "Run multi-step cognitive pipeline", "completed_segments": ()},
            context=run_context,
        )
    )

    assert result.get("completed_segments") == (s1, s2, s3)
    assert result.get("turn_outcome") == PlannerTurnOutcome(response="R3")


def test_subsequent_human_turn_starts_with_fresh_completed_segments(
    db_session: Session,
) -> None:
    """Each subsequent non-interrupted Human turn starts with empty segments and does not recommit
    prior segments.
    """
    s1 = ConversationSegment(messages=_messages("First request", "First response"))
    s2 = ConversationSegment(messages=_messages("Second request", "Second response"))

    planner = _planner(
        (
            PlannerOutput(result=PlannerResult(response="First response"), segment=s1),
            PlannerOutput(result=PlannerResult(response="Second response"), segment=s2),
        ),
        db_session,
    )

    _, turn1_segments = asyncio.run(
        planner.handle_message("First request", context=PlannerContext())
    )
    assert turn1_segments == (s1,)

    _, turn2_segments = asyncio.run(
        planner.handle_message("Second request", context=PlannerContext())
    )
    assert turn2_segments == (s2,)


def test_interrupt_resume_turn_boundary_isolates_segments(
    db_session: Session,
) -> None:
    """Segments from turn 1 before interrupt belong to turn 1; resumed turn accumulates freshly."""
    candidate = _candidate_result()
    assert candidate.plan is not None
    s1 = ConversationSegment(messages=_messages("Propose plan", "Proposed"))
    s2 = ConversationSegment(messages=_messages("Clarify proposal", "Clarification"))

    planner = _planner(
        (
            PlannerOutput(result=candidate, segment=s1),
            PlannerOutput(result=PlannerResult(response="Clarification"), segment=s2),
        ),
        db_session,
    )

    outcome_1, turn1_segments = asyncio.run(
        planner.handle_message("Propose plan", context=PlannerContext())
    )
    assert outcome_1.proposed_plan == candidate.plan
    assert turn1_segments == (s1,)
    assert _is_waiting(planner)

    outcome_2, turn2_segments = asyncio.run(
        planner.handle_message("Clarify proposal", context=PlannerContext())
    )
    assert outcome_2.response == "Clarification"
    assert turn2_segments == (s2,)


def test_failed_or_incomplete_model_invocation_does_not_commit_segment(
    db_session: Session,
) -> None:
    """Controlled error outcomes produce zero completed segments."""
    planner = _planner(
        (
            PlannerOutput(
                result=PlannerResult(response="Model failed"),
                segment=None,
                error=PlannerControlledError(
                    code=PlannerErrorCode.MODEL_UNAVAILABLE,
                    message="Model unavailable",
                ),
            ),
        ),
        db_session,
    )

    outcome, segments = asyncio.run(planner.handle_message("Try request", context=PlannerContext()))
    assert outcome.error is not None
    assert segments == ()

    empty_outcome, empty_segments = asyncio.run(
        planner.handle_message("   ", context=PlannerContext())
    )
    assert empty_outcome.error is not None
    assert empty_segments == ()
