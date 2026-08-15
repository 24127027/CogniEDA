from __future__ import annotations

import asyncio
from collections.abc import Iterable
from dataclasses import fields
from typing import Any, cast
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
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
from cognieda.agents.planner.types import PlannerOutput, PlannerResult
from cognieda.application.ports import AgentFactoryPort
from cognieda.application.services import PlanAdmissionService
from cognieda.delegation import ExecutorDispatcher
from cognieda.infrastructure.persistence.repositories import (
    ActivePlanRepository,
    ObjectiveRepository,
    PlanRepository,
    TaskRepository,
)
from cognieda.runtime import planner_runtime as planner_runtime_module
from cognieda.runtime.application import Application
from cognieda.runtime.event_bus import EventBus
from cognieda.runtime.events import (
    HumanInputRequested,
    MessageProduced,
    PlanProposed,
    RuntimeEvent,
)
from cognieda.runtime.planner_context import PlannerContextProvider
from cognieda.runtime.planner_runtime import (
    PlannerGraphState,
    PlannerRuntime,
    PlannerRuntimeContext,
    PlannerTurnOutcome,
)
from cognieda.runtime.workspace import Workspace
from cognieda.schemas import Objective, Plan, SessionFrame, Task, TaskKind


def _messages(request: str, response: str) -> tuple[ModelMessage, ...]:
    return (
        ModelRequest(parts=[UserPromptPart(content=request)]),
        ModelResponse(parts=[TextPart(content=response)]),
    )


class SequencePlanner:
    def __init__(self, outputs: Iterable[PlannerOutput]) -> None:
        self._outputs = iter(outputs)
        self.requests: list[str] = []
        self.contexts: list[PlannerContext] = []
        self.candidates: list[tuple[Plan | None, tuple[Task, ...]]] = []
        self.message_histories: list[tuple[ModelMessage, ...]] = []

    async def run(
        self,
        request: str,
        *,
        context: PlannerContext,
        candidate_plan: Plan | None = None,
        candidate_tasks: tuple[Task, ...] = (),
        message_history: list[ModelMessage] | None = None,
    ) -> PlannerOutput:
        self.requests.append(request)
        self.contexts.append(context)
        self.candidates.append((candidate_plan, candidate_tasks))
        self.message_histories.append(tuple(message_history or ()))
        return next(self._outputs)

    async def reload(self, **_: Any) -> None:
        pass


class RecordingDispatcher:
    def __init__(self) -> None:
        self.requests: list[object] = []

    async def dispatch(self, request: object) -> None:
        self.requests.append(request)


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
    plan = Plan.create(
        objective=objective,
        task_ids=(task.task_id,),
        tasks=(task,),
    )
    return PlannerResult(
        plan=plan,
        tasks=(task,),
        response=response,
    )


def _application(
    planner: SequencePlanner,
    db_session: Session,
    *,
    dispatcher: RecordingDispatcher | None = None,
) -> tuple[Application, list[RuntimeEvent]]:
    event_bus = EventBus()
    events: list[RuntimeEvent] = []
    event_bus.subscribe(MessageProduced, events.append)
    event_bus.subscribe(PlanProposed, events.append)
    event_bus.subscribe(HumanInputRequested, events.append)
    application = Application(
        workspace=cast(Workspace, object()),
        planner_agent=cast(Planner, planner),
        dispatcher=cast(ExecutorDispatcher, dispatcher or RecordingDispatcher()),
        agent_factory=cast(AgentFactoryPort, object()),
        event_bus=event_bus,
        session=db_session,
    )
    return application, events


def _state(application: Application) -> PlannerGraphState:
    return asyncio.run(application.planner_runtime.get_state())


def test_graph_and_runtime_context_have_exact_separate_ownership() -> None:
    assert tuple(PlannerGraphState.__annotations__) == (
        "latest_human_input",
        "candidate_plan",
        "candidate_tasks",
        "messages",
        "result",
        "error",
        "turn_outcome",
    )
    assert "context" not in PlannerGraphState.__annotations__
    assert tuple(field.name for field in fields(PlannerRuntimeContext)) == (
        "planner",
        "planner_context_provider",
        "plan_admission",
    )
    assert "candidate_plan" not in {field.name for field in fields(PlannerRuntimeContext)}
    assert tuple(PlannerTurnOutcome.model_fields) == (
        "candidate_plan",
        "candidate_tasks",
        "response",
        "human_input_request",
        "candidate_admitted",
        "candidate_discarded",
        "active_plan_continuation_deferred",
        "awaiting_human",
        "error",
    )


def test_candidate_state_rejects_orphan_and_mismatched_task_bundles() -> None:
    objective = Objective(text="Understand customer churn.")
    expected = _candidate_result(objective=objective)
    unexpected = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="Unexpected replacement.",
    )
    empty = PlannerGraphState(
        latest_human_input=None,
        candidate_plan=None,
        candidate_tasks=(unexpected,),
        messages=(),
        result=None,
        error=None,
        turn_outcome=None,
    )
    with pytest.raises(ValueError, match="require a retained candidate Plan"):
        planner_runtime_module._validate_candidate_state(empty)

    assert expected.plan is not None
    mismatch = empty.copy()
    mismatch["candidate_plan"] = expected.plan
    with pytest.raises(ValueError, match="exactly match"):
        planner_runtime_module._validate_candidate_state(mismatch)


def test_candidate_proposal_is_checkpointed_and_published_without_authoritative_writes(
    db_session: Session,
) -> None:
    messages = _messages("Investigate churn.", "Proposed a plan.")
    candidate = _candidate_result()
    assert candidate.plan is not None
    planner = SequencePlanner((PlannerOutput(result=candidate, messages=messages),))
    application, events = _application(planner, db_session)

    asyncio.run(application.submit_message("Investigate churn."))
    state = _state(application)

    assert planner.requests == ["Investigate churn."]
    assert planner.message_histories == [()]
    assert state["candidate_plan"] == candidate.plan
    assert state["candidate_tasks"] == candidate.tasks
    assert state["messages"] == messages
    assert asyncio.run(application.planner_runtime.is_waiting_for_human()) is True
    assert isinstance(events[0], PlanProposed)
    assert events[0].plan == candidate.plan
    assert events[0].tasks == candidate.tasks
    assert isinstance(events[1], MessageProduced)
    assert events[1].message.content == candidate.response
    assert not hasattr(application, "conversation_history")
    assert not hasattr(application, "_pending_plan")
    assert not hasattr(application, "_pending_tasks")
    assert ObjectiveRepository(db_session).get_by_id(candidate.plan.objective.objective_id) is None
    assert TaskRepository(db_session).get_by_id(candidate.tasks[0].task_id) is None
    assert PlanRepository(db_session).get_by_id(candidate.plan.plan_id) is None


def test_natural_multiturn_review_retain_replace_and_authorize_exact_candidate(
    db_session: Session,
    monkeypatch,
) -> None:
    objective = Objective(text="Understand customer churn.")
    p1 = _candidate_result(objective=objective, instruction="Analyze pricing cohorts.")
    p2 = _candidate_result(objective=objective, instruction="Analyze support cohorts.")
    assert p1.plan is not None
    assert p2.plan is not None
    first_messages = _messages("Investigate churn.", "P1")
    explanation_messages = _messages("Why is pricing included?", "Explanation")
    replacement_messages = _messages("Remove pricing.", "P2")
    authorization_messages = _messages("That looks right, proceed.", "Authorized")
    outputs = (
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
    )
    planner = SequencePlanner(outputs)
    admission_calls: list[tuple[Plan, tuple[Task, ...]]] = []
    original_admit = PlanAdmissionService.admit

    def record_admit(
        self: PlanAdmissionService,
        plan: Plan,
        *,
        tasks: tuple[Task, ...],
    ) -> Plan:
        admission_calls.append((plan, tasks))
        return original_admit(self, plan, tasks=tasks)

    monkeypatch.setattr(PlanAdmissionService, "admit", record_admit)
    application, events = _application(planner, db_session)

    asyncio.run(application.submit_message("Investigate churn."))
    assert _state(application)["candidate_plan"] == p1.plan
    assert PlanRepository(db_session).get_by_id(p1.plan.plan_id) is None

    asyncio.run(application.submit_message("Why is pricing included?"))
    explanation_state = _state(application)
    assert explanation_state["candidate_plan"] == p1.plan
    assert explanation_state["candidate_tasks"] == p1.tasks
    assert planner.candidates[1] == (p1.plan, p1.tasks)
    assert admission_calls == []

    asyncio.run(application.submit_message("Remove pricing."))
    replacement_state = _state(application)
    assert replacement_state["candidate_plan"] == p2.plan
    assert replacement_state["candidate_tasks"] == p2.tasks
    assert replacement_state["candidate_plan"] != p1.plan
    assert admission_calls == []

    asyncio.run(application.submit_message("That looks right, proceed."))
    final_state = _state(application)
    assert admission_calls == [(p2.plan, p2.tasks)]
    assert final_state["candidate_plan"] is None
    assert final_state["candidate_tasks"] == ()
    assert final_state["turn_outcome"] is not None
    assert final_state["turn_outcome"].candidate_admitted is True
    assert ActivePlanRepository(db_session).get_by_objective_id(objective.objective_id) == p2.plan
    assert application.session_frame.objective is None
    assert asyncio.run(application.planner_runtime.is_waiting_for_human()) is False
    assert planner.requests == [
        "Investigate churn.",
        "Why is pricing included?",
        "Remove pricing.",
        "That looks right, proceed.",
    ]
    assert planner.message_histories == [
        (),
        first_messages,
        (
            *first_messages,
            *explanation_messages,
        ),
        (
            *first_messages,
            *explanation_messages,
            *replacement_messages,
        ),
    ]
    assert sum(isinstance(event, PlanProposed) for event in events) == 2
    assert isinstance(events[-1], MessageProduced)
    assert events[-1].message.content == "The proposed Plan was admitted and activated."


def test_planner_context_is_freshly_materialized_on_every_cognitive_invocation(
    db_session: Session,
) -> None:
    first_messages = _messages("First question.", "First answer.")
    second_messages = _messages("Second question.", "Second answer.")
    planner = SequencePlanner(
        (
            PlannerOutput(
                result=PlannerResult(response="First answer."),
                messages=first_messages,
            ),
            PlannerOutput(
                result=PlannerResult(response="Second answer."),
                messages=second_messages,
            ),
        )
    )
    application, _ = _application(planner, db_session)
    first_objective = Objective(text="First current Objective.")
    second_objective = Objective(text="Second current Objective.")
    application.session_frame = SessionFrame(objective=first_objective)

    asyncio.run(application.submit_message("First question."))
    application.session_frame = SessionFrame(objective=second_objective)
    asyncio.run(application.submit_message("Second question."))

    assert planner.contexts[0].objective == first_objective
    assert planner.contexts[1].objective == second_objective
    assert planner.contexts[0] is not planner.contexts[1]
    assert "PlannerContext" not in PlannerGraphState.__annotations__
    assert _state(application)["messages"] == (*first_messages, *second_messages)


def test_human_clarification_retains_candidate_and_interrupts_again(
    db_session: Session,
) -> None:
    candidate = _candidate_result()
    assert candidate.plan is not None
    planner = SequencePlanner(
        (
            PlannerOutput(result=candidate),
            PlannerOutput(
                result=PlannerResult(human_input_request="Which cohort is in scope?")
            ),
        )
    )
    application, events = _application(planner, db_session)

    asyncio.run(application.submit_message("Investigate churn."))
    asyncio.run(application.submit_message("Can you narrow that down?"))

    assert _state(application)["candidate_plan"] == candidate.plan
    assert asyncio.run(application.planner_runtime.is_waiting_for_human()) is True
    assert isinstance(events[-1], HumanInputRequested)
    assert events[-1].message.content == "Which cohort is in scope?"
    assert PlanRepository(db_session).get_by_id(candidate.plan.plan_id) is None


def test_discard_clears_candidate_and_discard_without_candidate_fails_closed(
    db_session: Session,
) -> None:
    candidate = _candidate_result()
    planner = SequencePlanner(
        (
            PlannerOutput(result=candidate),
            PlannerOutput(
                result=PlannerResult(
                    response="I discarded the proposal.",
                    discard_candidate=True,
                )
            ),
            PlannerOutput(result=PlannerResult(discard_candidate=True)),
        )
    )
    application, events = _application(planner, db_session)

    asyncio.run(application.submit_message("Investigate churn."))
    asyncio.run(application.submit_message("Abandon that proposal."))
    discarded = _state(application)
    assert discarded["candidate_plan"] is None
    assert discarded["turn_outcome"] is not None
    assert discarded["turn_outcome"].candidate_discarded is True
    assert asyncio.run(application.planner_runtime.is_waiting_for_human()) is False

    asyncio.run(application.submit_message("Discard it again."))
    invalid = _state(application)
    assert invalid["error"] is not None
    assert invalid["error"].code.value == "invalid_lifecycle_state"
    assert isinstance(events[-1], MessageProduced)
    assert events[-1].message.type.value == "error"


def test_admission_failure_retains_exact_candidate_and_reports_controlled_error(
    db_session: Session,
) -> None:
    candidate = _candidate_result()
    assert candidate.plan is not None
    existing = ObjectiveRepository(db_session).create(
        Objective(objective_id=candidate.plan.objective.objective_id, text="Collision")
    )
    assert existing != candidate.plan.objective
    planner = SequencePlanner(
        (
            PlannerOutput(result=candidate),
            PlannerOutput(result=PlannerResult(continue_execution=True)),
        )
    )
    application, events = _application(planner, db_session)

    asyncio.run(application.submit_message("Investigate churn."))
    asyncio.run(application.submit_message("Proceed with that exact proposal."))
    state = _state(application)

    assert state["candidate_plan"] == candidate.plan
    assert state["candidate_tasks"] == candidate.tasks
    assert state["error"] is not None
    assert state["error"].code.value == "plan_admission_failed"
    assert PlanRepository(db_session).get_by_id(candidate.plan.plan_id) is None
    assert isinstance(events[-1], MessageProduced)
    assert events[-1].message.type.value == "error"


def test_active_plan_continuation_is_visible_and_never_dispatches(
    db_session: Session,
) -> None:
    candidate = _candidate_result()
    assert candidate.plan is not None
    PlanAdmissionService(db_session).admit(candidate.plan, tasks=candidate.tasks)
    planner = SequencePlanner(
        (PlannerOutput(result=PlannerResult(continue_execution=True)),)
    )
    dispatcher = RecordingDispatcher()
    application, events = _application(planner, db_session, dispatcher=dispatcher)
    application.session_frame = SessionFrame(objective=candidate.plan.objective)

    asyncio.run(application.submit_message("Continue active work."))

    assert planner.contexts[0].active_plan == candidate.plan
    assert _state(application)["candidate_plan"] is None
    assert len(events) == 1
    assert isinstance(events[0], MessageProduced)
    assert "execution is not implemented" in str(events[0].message.content)
    assert ActivePlanRepository(db_session).get_by_objective_id(
        candidate.plan.objective.objective_id
    ) == candidate.plan
    assert dispatcher.requests == []


def test_inmemory_checkpointer_isolates_runtime_thread_identity(
    db_session: Session,
) -> None:
    first = _candidate_result(instruction="First thread task.")
    second = _candidate_result(instruction="Second thread task.")
    provider = PlannerContextProvider(
        session_frame_provider=SessionFrame,
        active_plans=ActivePlanRepository(db_session),
    )
    first_runtime = PlannerRuntime(
        runtime_context=PlannerRuntimeContext(
            planner=cast(Planner, SequencePlanner((PlannerOutput(result=first),))),
            planner_context_provider=provider,
            plan_admission=PlanAdmissionService(db_session),
        ),
        thread_id=uuid4(),
    )
    second_runtime = PlannerRuntime(
        runtime_context=PlannerRuntimeContext(
            planner=cast(Planner, SequencePlanner((PlannerOutput(result=second),))),
            planner_context_provider=provider,
            plan_admission=PlanAdmissionService(db_session),
        ),
        checkpointer=first_runtime.checkpointer,
        thread_id=uuid4(),
    )

    asyncio.run(first_runtime.handle_message("First request."))

    assert asyncio.run(first_runtime.get_state())["candidate_plan"] == first.plan
    assert asyncio.run(second_runtime.get_state())["candidate_plan"] is None
    assert first_runtime.thread_id != second_runtime.thread_id

    asyncio.run(second_runtime.handle_message("Second request."))
    assert asyncio.run(second_runtime.get_state())["candidate_plan"] == second.plan
    assert asyncio.run(first_runtime.get_state())["candidate_plan"] == first.plan


def test_application_has_no_separate_plan_review_or_history_authority() -> None:
    assert not hasattr(Application, "review_plan")
    assert not hasattr(Application, "_apply_planner_result")
    assert not hasattr(Application, "conversation_history")


def test_skill_assignment_reloads_tooling_and_planner_without_state_mutation(
    db_session: Session,
) -> None:
    workspace = Mock(spec=Workspace)
    workspace.project_config = Mock()
    workspace.project_config.try_resolve_model.return_value = None
    planner = Mock(spec=Planner)
    planner.reload = AsyncMock()
    agent_factory = Mock()
    application = Application(
        workspace=workspace,
        planner_agent=planner,
        dispatcher=cast(ExecutorDispatcher, object()),
        agent_factory=cast(AgentFactoryPort, agent_factory),
        event_bus=EventBus(),
        session=db_session,
    )
    events: list[MessageProduced] = []
    application.event_bus.subscribe(MessageProduced, events.append)
    original_frame = application.session_frame

    asyncio.run(application.submit_message("/skill use planner review"))

    workspace.add_worker_skill.assert_called_once_with("planner", "review")
    agent_factory.reload_tooling.assert_called_once_with()
    planner.reload.assert_awaited_once_with(
        model_config=None,
        agent_instruction=None,
        recreate_agent=True,
    )
    planner.run.assert_not_called()
    assert application.session_frame is original_frame
    assert [event.message.content for event in events] == ["Assigned 'review' to 'planner'."]


def test_provider_and_reload_commands_publish_user_visible_messages(
    db_session: Session,
) -> None:
    workspace = Mock(spec=Workspace)
    provider = Mock()
    provider.model = "test-model"
    provider.api_key_configured.return_value = True
    workspace.project_config = Mock()
    workspace.project_config.default_provider = "openai"
    workspace.project_config.providers = {"openai": provider}
    workspace.load_agent_instruction.return_value = "reloaded instructions"
    planner = Mock(spec=Planner)
    planner.reload = AsyncMock()
    event_bus = EventBus()
    events: list[MessageProduced] = []
    event_bus.subscribe(MessageProduced, events.append)
    application = Application(
        workspace=workspace,
        planner_agent=planner,
        dispatcher=cast(ExecutorDispatcher, object()),
        agent_factory=cast(AgentFactoryPort, Mock()),
        event_bus=event_bus,
        session=db_session,
    )

    asyncio.run(application.submit_message("/provider"))
    asyncio.run(application.submit_message("/reload"))

    assert [event.message.content for event in events] == [
        (
            "Current provider : openai\n"
            "        Model            : test-model\n"
            "        API key          : yes"
        ),
        "Planner instructions reloaded.",
    ]
    planner.reload.assert_awaited_once_with(
        model_config=None,
        agent_instruction="reloaded instructions",
        recreate_agent=False,
    )
