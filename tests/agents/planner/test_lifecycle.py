from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Any, cast
from uuid import UUID, uuid4

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
from cognieda.agents.planner.context import PlannerContext
from cognieda.agents.planner.dependencies import PlannerDeps
from cognieda.agents.planner.graph import InProcessPlannerSerializer, build_graph
from cognieda.agents.planner.state import (
    PlannerGraphInput,
    PlannerGraphOutput,
    PlannerState,
    PlannerTurnOutcome,
)
from cognieda.agents.planner.types import PlannerErrorCode, PlannerOutput, PlannerResult
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


class MutableContextProvider:
    def __init__(self, context: PlannerContext | None = None) -> None:
        self.current = context or PlannerContext()

    def materialize(self) -> PlannerContext:
        return self.current.model_copy()


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
            deps=PlannerDeps(dispatcher=self.recording_dispatcher),
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
        "messages",
        "turn_outcome",
    )
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
    messages = _messages("Investigate churn.", "Proposed a plan.")
    candidate = _candidate_result()
    assert candidate.plan is not None
    planner = _planner(
        (PlannerOutput(result=candidate, messages=messages),),
        db_session,
    )

    outcome = asyncio.run(
        planner.handle_message("Investigate churn.", context=PlannerContext())
    )
    state = _state(planner)
    persisted_candidate = state["candidate_plan"]

    assert outcome.proposed_plan == candidate.plan
    assert persisted_candidate == candidate.plan
    assert persisted_candidate is not None
    assert persisted_candidate.tasks == candidate.plan.tasks
    assert state["messages"] == messages
    assert _is_waiting(planner)
    assert ObjectiveRepository(db_session).get_by_id(
        candidate.plan.objective.objective_id
    ) is None
    assert TaskRepository(db_session).get_by_id(candidate.plan.tasks[0].task_id) is None
    assert PlanRepository(db_session).get_by_id(candidate.plan.plan_id) is None


def test_empty_human_input_is_rejected_before_interrupt_resume(
    db_session: Session,
) -> None:
    candidate = _candidate_result()
    assert candidate.plan is not None
    first_messages = _messages("Investigate churn.", "Proposed a plan.")
    planner = _planner(
        (
            PlannerOutput(result=candidate, messages=first_messages),
            PlannerOutput(result=PlannerResult(response="The candidate remains available.")),
        ),
        db_session,
    )

    asyncio.run(planner.handle_message("Investigate churn.", context=PlannerContext()))
    before = _state(planner)
    rejected = asyncio.run(planner.handle_message("  ", context=PlannerContext()))

    assert rejected.error is not None
    assert rejected.error.code is PlannerErrorCode.INVALID_REQUEST
    assert planner.requests == ["Investigate churn."]
    assert _state(planner) == before
    assert _is_waiting(planner)

    resumed = asyncio.run(planner.handle_message("Why this scope?", context=PlannerContext()))
    assert resumed.response == "The candidate remains available."
    assert planner.requests == ["Investigate churn.", "Why this scope?"]


def test_natural_multiturn_review_retain_replace_and_authorize_exact_candidate(
    db_session: Session,
) -> None:
    objective = Objective(text="Understand customer churn.")
    p1 = _candidate_result(objective=objective, instruction="Analyze pricing cohorts.")
    p2 = _candidate_result(objective=objective, instruction="Analyze support cohorts.")
    assert p1.plan is not None and p2.plan is not None
    first_messages = _messages("Investigate churn.", "P1")
    explanation_messages = _messages("Why is pricing included?", "Explanation")
    replacement_messages = _messages("Remove pricing.", "P2")
    authorization_messages = _messages("That looks right, proceed.", "Authorized")
    admission = RecordingAdmission(PlanAdmissionService(db_session))
    planner = _planner(
        (
            PlannerOutput(result=p1, messages=first_messages),
            PlannerOutput(
                result=PlannerResult(response="Pricing was included as a possible driver."),
                messages=explanation_messages,
            ),
            PlannerOutput(result=p2, messages=replacement_messages),
            PlannerOutput(
                result=PlannerResult(continue_execution=True),
                messages=authorization_messages,
            ),
        ),
        db_session,
        plan_admission=admission,
    )
    context = PlannerContext(objective=objective)

    first = asyncio.run(planner.handle_message("Investigate churn.", context=context))
    assert first.proposed_plan == p1.plan
    assert _state(planner)["candidate_plan"] == p1.plan

    explanation = asyncio.run(planner.handle_message("Why is pricing included?", context=context))
    assert explanation.proposed_plan is None
    assert _state(planner)["candidate_plan"] == p1.plan
    assert planner.candidates[1] == p1.plan
    assert admission.calls == []

    replacement = asyncio.run(planner.handle_message("Remove pricing.", context=context))
    assert replacement.proposed_plan == p2.plan
    assert _state(planner)["candidate_plan"] == p2.plan
    assert admission.calls == []

    outcome = asyncio.run(planner.handle_message("That looks right, proceed.", context=context))
    assert admission.calls == [p2.plan]
    assert _state(planner)["candidate_plan"] is None
    assert outcome.response == "The proposed Plan was admitted and activated."
    assert ActivePlanRepository(db_session).get_by_objective_id(
        objective.objective_id
    ) == p2.plan
    assert not _is_waiting(planner)
    assert planner.message_histories == [
        (),
        first_messages,
        (*first_messages, *explanation_messages),
        (*first_messages, *explanation_messages, *replacement_messages),
    ]


def test_context_is_fresh_and_native_history_remains_graph_owned(
    db_session: Session,
) -> None:
    first_messages = _messages("First question.", "First answer.")
    second_messages = _messages("Second question.", "Second answer.")
    session_frames = SessionFrameRepository(db_session, scope_key="fresh-context")
    planner = _planner(
        (
            PlannerOutput(result=PlannerResult(response="First answer."), messages=first_messages),
            PlannerOutput(
                result=PlannerResult(response="Second answer."),
                messages=second_messages,
            ),
        ),
        db_session,
    )
    first_objective = Objective(text="First current Objective.")
    second_objective = Objective(text="Second current Objective.")
    session_frames.save_current(SessionFrame(objective=first_objective))

    context_1 = build_planner_context(session_frames.get_current())
    asyncio.run(planner.handle_message("First question.", context=context_1))

    session_frames.save_current(SessionFrame(objective=second_objective))
    context_2 = build_planner_context(session_frames.get_current())
    asyncio.run(planner.handle_message("Second question.", context=context_2))

    assert planner.contexts[0].objective == first_objective
    assert planner.contexts[1].objective == second_objective
    assert planner.contexts[0] is not planner.contexts[1]
    assert planner.message_histories == [(), first_messages]
    assert _state(planner)["messages"] == (*first_messages, *second_messages)
    assert "context" not in PlannerState.__annotations__


def test_custom_serializer_is_required_for_nested_typed_plan_state() -> None:
    candidate = _candidate_result()
    assert candidate.plan is not None
    state = {
        "candidate_plan": candidate.plan,
        "messages": _messages("Question.", "Answer."),
    }

    plain_serializer = InMemorySaver().serde
    planner_serializer = InProcessPlannerSerializer()
    plain = plain_serializer.loads_typed(plain_serializer.dumps_typed(state))
    restored = planner_serializer.loads_typed(planner_serializer.dumps_typed(state))

    assert isinstance(plain["candidate_plan"], Plan)
    assert not isinstance(plain["candidate_plan"].tasks[0], Task)
    assert restored == state
    assert isinstance(restored["candidate_plan"].tasks[0], Task)
    assert isinstance(restored["messages"], tuple)


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
    discarded = asyncio.run(
        planner.handle_message("Abandon that proposal.", context=PlannerContext())
    )
    assert _state(planner)["candidate_plan"] is None
    assert discarded.response == "I discarded the proposal."
    assert not _is_waiting(planner)

    invalid = asyncio.run(
        planner.handle_message("Discard it again.", context=PlannerContext())
    )
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
    outcome = asyncio.run(
        planner.handle_message("Proceed with that exact proposal.", context=PlannerContext())
    )
    persisted_candidate = _state(planner)["candidate_plan"]

    assert persisted_candidate == candidate.plan
    assert persisted_candidate is not None
    assert persisted_candidate.tasks == candidate.plan.tasks
    assert outcome.error is not None
    assert outcome.error.code.value == "plan_admission_failed"
    assert PlanRepository(db_session).get_by_id(candidate.plan.plan_id) is None


def test_active_plan_continuation_is_visible_and_never_dispatches(
    db_session: Session,
) -> None:
    candidate = _candidate_result()
    assert candidate.plan is not None
    PlanAdmissionService(db_session).admit(candidate.plan)
    dispatcher = RecordingDispatcher()
    context = PlannerContext(active_plan=candidate.plan, objective=candidate.plan.objective)
    planner = _planner(
        (PlannerOutput(result=PlannerResult(continue_execution=True)),),
        db_session,
        dispatcher=dispatcher,
    )

    outcome = asyncio.run(planner.handle_message("Continue active work.", context=context))

    assert planner.contexts[0].active_plan == candidate.plan
    assert _state(planner)["candidate_plan"] is None
    assert outcome.response is not None
    assert "execution is not implemented" in outcome.response
    assert dispatcher.requests == []


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


def test_interrupt_resume_receives_fresh_context_while_preserving_candidate_and_history(
    db_session: Session,
) -> None:
    """Turn 1 interrupts with C1; Turn 2 resumes with C2 and sees C2 in plan_or_answer."""
    objective_1 = Objective(text="Initial objective S1.")
    objective_2 = Objective(text="Changed authoritative objective S2.")
    candidate = _candidate_result(objective=objective_1, instruction="Profile S1 data.")
    assert candidate.plan is not None

    turn1_messages = _messages("Propose plan.", "Here is the proposal.")
    turn2_messages = _messages("Explain why S2 matters.", "Here is the explanation for S2.")

    planner = _planner(
        (
            PlannerOutput(result=candidate, messages=turn1_messages),
            PlannerOutput(
                result=PlannerResult(response="Explanation with fresh context."),
                messages=turn2_messages,
            ),
        ),
        db_session,
    )

    # Turn 1: Propose candidate -> awaits human review
    context_1 = PlannerContext(objective=objective_1)
    outcome_1 = asyncio.run(planner.handle_message("Propose plan.", context=context_1))
    assert outcome_1.proposed_plan == candidate.plan
    assert _is_waiting(planner)
    assert _state(planner)["candidate_plan"] == candidate.plan
    assert len(planner.contexts) == 1
    assert planner.contexts[0].objective == objective_1

    # Between turns: authoritative state changes to S2
    context_2 = PlannerContext(objective=objective_2)

    # Turn 2: Human asks a question while candidate is waiting (resumes interrupt)
    outcome_2 = asyncio.run(
        planner.handle_message("Explain why S2 matters.", context=context_2)
    )

    assert outcome_2.response == "Explanation with fresh context."


    # Invariant checks:
    # 1. plan_or_answer in Turn 2 received context_2 (S2)
    assert len(planner.contexts) == 2
    assert planner.contexts[1].objective == objective_2
    assert planner.contexts[1] is not planner.contexts[0]

    # 2. Retained candidate survives across the interrupt-resume boundary
    assert _state(planner)["candidate_plan"] == candidate.plan
    assert planner.candidates[1] == candidate.plan

    # 3. Model message history survives across the interrupt-resume boundary
    assert planner.message_histories[1] == turn1_messages
    assert _state(planner)["messages"] == (*turn1_messages, *turn2_messages)


def test_planner_context_is_not_checkpointed(db_session: Session) -> None:
    """Checkpointer must store only lifecycle state, never PlannerContext."""
    objective = Objective(text="Scope verification.")
    planner = _planner(
        (PlannerOutput(result=PlannerResult(response="Done.")),),
        db_session,
    )
    context = PlannerContext(objective=objective)
    asyncio.run(planner.handle_message("Run test.", context=context))

    snapshot = _snapshot(planner)
    values = snapshot.values
    assert isinstance(values, dict)
    assert "context" not in values
    assert "planner_context" not in values
    assert not any(isinstance(v, PlannerContext) for v in values.values())


def test_build_graph_schema_types() -> None:
    """build_graph must declare StateGraph with correct StateT, ContextT, InputT, OutputT."""
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

    # Verify builder schemas
    builder = graph.builder
    assert builder.state_schema is PlannerState
    assert builder.context_schema is PlannerContext
    assert builder.input_schema is PlannerGraphInput
    assert builder.output_schema is PlannerGraphOutput

