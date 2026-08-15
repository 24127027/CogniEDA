from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Any, cast
from uuid import UUID, uuid4

from langgraph.checkpoint.base import BaseCheckpointSaver
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
from cognieda.agents.planner.state import PlannerState, PlannerTurnOutcome
from cognieda.agents.planner.types import PlannerOutput, PlannerResult
from cognieda.application.ports import AgentFactoryPort
from cognieda.application.services import PlanAdmissionService
from cognieda.infrastructure.persistence.repositories import (
    ActivePlanRepository,
    ObjectiveRepository,
    PlanRepository,
    TaskRepository,
)
from cognieda.schemas import Objective, Plan, Task, TaskKind


def _messages(request: str, response: str) -> tuple[ModelMessage, ...]:
    return (
        ModelRequest(parts=[UserPromptPart(content=request)]),
        ModelResponse(parts=[TextPart(content=response)]),
    )


class RecordingDispatcher:
    def __init__(self) -> None:
        self.requests: list[object] = []

    async def dispatch(self, request: object) -> None:
        self.requests.append(request)


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
        context_provider: MutableContextProvider,
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
            planner_context_provider=context_provider,
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
    context_provider: MutableContextProvider | None = None,
    plan_admission: PlanAdmissionService | RecordingAdmission | None = None,
    dispatcher: RecordingDispatcher | None = None,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
    thread_id: UUID | None = None,
) -> SequencePlanner:
    return SequencePlanner(
        outputs,
        context_provider=context_provider or MutableContextProvider(),
        plan_admission=plan_admission or PlanAdmissionService(db_session),
        dispatcher=dispatcher,
        checkpointer=checkpointer,
        thread_id=thread_id,
    )


def _snapshot(planner: Planner):
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

    outcome = asyncio.run(planner.handle_message("Investigate churn."))
    state = _state(planner)

    assert outcome.proposed_plan == candidate.plan
    assert state["candidate_plan"] == candidate.plan
    assert state["candidate_plan"].tasks == candidate.plan.tasks
    assert state["messages"] == messages
    assert _is_waiting(planner)
    assert ObjectiveRepository(db_session).get_by_id(
        candidate.plan.objective.objective_id
    ) is None
    assert TaskRepository(db_session).get_by_id(candidate.plan.tasks[0].task_id) is None
    assert PlanRepository(db_session).get_by_id(candidate.plan.plan_id) is None


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

    first = asyncio.run(planner.handle_message("Investigate churn."))
    assert first.proposed_plan == p1.plan
    assert _state(planner)["candidate_plan"] == p1.plan

    explanation = asyncio.run(planner.handle_message("Why is pricing included?"))
    assert explanation.proposed_plan is None
    assert _state(planner)["candidate_plan"] == p1.plan
    assert planner.candidates[1] == p1.plan
    assert admission.calls == []

    replacement = asyncio.run(planner.handle_message("Remove pricing."))
    assert replacement.proposed_plan == p2.plan
    assert _state(planner)["candidate_plan"] == p2.plan
    assert admission.calls == []

    outcome = asyncio.run(planner.handle_message("That looks right, proceed."))
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
    provider = MutableContextProvider()
    planner = _planner(
        (
            PlannerOutput(result=PlannerResult(response="First answer."), messages=first_messages),
            PlannerOutput(
                result=PlannerResult(response="Second answer."),
                messages=second_messages,
            ),
        ),
        db_session,
        context_provider=provider,
    )
    first_objective = Objective(text="First current Objective.")
    second_objective = Objective(text="Second current Objective.")
    provider.current = PlannerContext(objective=first_objective)

    asyncio.run(planner.handle_message("First question."))
    provider.current = PlannerContext(objective=second_objective)
    asyncio.run(planner.handle_message("Second question."))

    assert planner.contexts[0].objective == first_objective
    assert planner.contexts[1].objective == second_objective
    assert planner.contexts[0] is not planner.contexts[1]
    assert planner.message_histories == [(), first_messages]
    assert _state(planner)["messages"] == (*first_messages, *second_messages)


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

    asyncio.run(planner.handle_message("Investigate churn."))
    discarded = asyncio.run(planner.handle_message("Abandon that proposal."))
    assert _state(planner)["candidate_plan"] is None
    assert discarded.response == "I discarded the proposal."
    assert not _is_waiting(planner)

    invalid = asyncio.run(planner.handle_message("Discard it again."))
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

    asyncio.run(planner.handle_message("Investigate churn."))
    outcome = asyncio.run(planner.handle_message("Proceed with that exact proposal."))

    assert _state(planner)["candidate_plan"] == candidate.plan
    assert _state(planner)["candidate_plan"].tasks == candidate.plan.tasks
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
    provider = MutableContextProvider(
        PlannerContext(active_plan=candidate.plan, objective=candidate.plan.objective)
    )
    planner = _planner(
        (PlannerOutput(result=PlannerResult(continue_execution=True)),),
        db_session,
        context_provider=provider,
        dispatcher=dispatcher,
    )

    outcome = asyncio.run(planner.handle_message("Continue active work."))

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

    asyncio.run(first_planner.handle_message("First request."))
    assert _state(first_planner)["candidate_plan"] == first.plan
    assert not _snapshot(second_planner).values

    asyncio.run(second_planner.handle_message("Second request."))
    assert _state(second_planner)["candidate_plan"] == second.plan
    assert _state(first_planner)["candidate_plan"] == first.plan
