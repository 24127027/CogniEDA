from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Any, cast
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import ValidationError
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
from cognieda.execution import ExecutorDispatcher
from cognieda.infrastructure.persistence.repositories import (
    ActivePlanRepository,
    ObjectiveRepository,
    PlanRepository,
    TaskRepository,
)
from cognieda.runtime.application import Application
from cognieda.runtime.conversation import ConversationHistory, ConversationTurn
from cognieda.runtime.workspace import Workspace
from cognieda.schemas import Objective, Plan, Task, TaskKind


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

    async def run(self, request: str, *, context: PlannerContext) -> PlannerOutput:
        self.requests.append(request)
        self.contexts.append(context)
        return next(self._outputs)

    async def reload(self, **_: Any) -> None:
        pass


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


def _application(planner: SequencePlanner, db_session: Session) -> Application:
    return Application(
        workspace=cast(Workspace, object()),
        planner_agent=cast(Planner, planner),
        dispatcher=cast(ExecutorDispatcher, object()),
        agent_factory=cast(AgentFactoryPort, object()),
        session=db_session,
    )


def test_application_has_no_separate_plan_review_api() -> None:
    assert not hasattr(Application, "review_plan")


def test_conversation_history_appends_complete_native_message_turns() -> None:
    first_messages = _messages("First request", "First response")
    second_messages = _messages("Second request", "Second response")

    empty = ConversationHistory()
    first = empty.add_turn(first_messages)
    second = first.add_turn(second_messages)

    assert empty.turns == ()
    assert first.turns[0].messages == first_messages
    assert second.model_messages() == [*first_messages, *second_messages]
    with pytest.raises(ValidationError, match="at least one ModelMessage"):
        ConversationTurn(messages=())


def test_candidate_becomes_pending_only_and_pending_tasks_are_not_authoritative(
    db_session: Session,
) -> None:
    first_messages = _messages("Investigate churn.", "Proposed a plan.")
    candidate = _candidate_result()
    assert candidate.plan is not None
    planner = SequencePlanner((PlannerOutput(result=candidate, messages=first_messages),))
    application = _application(planner, db_session)

    first = asyncio.run(application.submit_message("Investigate churn."))

    assert first.content == "I propose a bounded investigation."
    assert application._pending_plan == candidate.plan
    assert application._pending_tasks == candidate.tasks
    assert application.session_frame.objective is None
    assert application.session_frame.tasks == ()
    assert len(application.conversation_history.turns) == 1
    assert planner.contexts[0].pending_plan is None
    assert planner.contexts[0].pending_tasks == ()
    assert ObjectiveRepository(db_session).get_by_id(
        candidate.plan.objective.objective_id
    ) is None
    assert TaskRepository(db_session).get_by_id(candidate.tasks[0].task_id) is None
    assert PlanRepository(db_session).get_by_id(candidate.plan.plan_id) is None
    assert ActivePlanRepository(db_session).get_by_objective_id(
        candidate.plan.objective.objective_id
    ) is None


def test_response_with_same_candidate_preserves_pending_bundle(
    db_session: Session,
) -> None:
    candidate = _candidate_result()
    assert candidate.plan is not None
    explained = candidate.model_copy(
        update={"response": "Segmentation separates materially different cohorts."}
    )
    planner = SequencePlanner((PlannerOutput(result=candidate), PlannerOutput(result=explained)))
    application = _application(planner, db_session)

    asyncio.run(application.submit_message("Investigate churn."))
    response = asyncio.run(application.submit_message("Why segment customers?"))

    assert planner.contexts[1].pending_plan == candidate.plan
    assert planner.contexts[1].pending_tasks == candidate.tasks
    assert planner.contexts[1].tasks == ()
    assert response.content == "Segmentation separates materially different cohorts."
    assert application._pending_plan == candidate.plan
    assert application._pending_tasks == candidate.tasks
    assert PlanRepository(db_session).get_by_id(candidate.plan.plan_id) is None


def test_new_candidate_replaces_pending_bundle_without_authoritative_writes(
    db_session: Session,
) -> None:
    first = _candidate_result()
    revised = _candidate_result(instruction="Profile enterprise churn labels.")
    assert first.plan is not None
    assert revised.plan is not None
    planner = SequencePlanner((PlannerOutput(result=first), PlannerOutput(result=revised)))
    application = _application(planner, db_session)

    asyncio.run(application.submit_message("Investigate churn."))
    asyncio.run(application.submit_message("Focus on enterprise customers."))

    assert application._pending_plan == revised.plan
    assert application._pending_tasks == revised.tasks
    assert PlanRepository(db_session).get_by_id(first.plan.plan_id) is None
    assert PlanRepository(db_session).get_by_id(revised.plan.plan_id) is None


def test_response_without_candidate_clears_stale_pending_bundle(
    db_session: Session,
) -> None:
    candidate = _candidate_result()
    assert candidate.plan is not None
    planner = SequencePlanner(
        (
            PlannerOutput(result=candidate),
            PlannerOutput(result=PlannerResult(response="I will stop this analysis.")),
        )
    )
    application = _application(planner, db_session)

    asyncio.run(application.submit_message("Investigate churn."))
    asyncio.run(application.submit_message("Stop this analysis."))

    assert application._pending_plan is None
    assert application._pending_tasks == ()
    assert PlanRepository(db_session).get_by_id(candidate.plan.plan_id) is None


def test_conversational_acceptance_admits_exact_prior_pending_bundle(
    db_session: Session,
) -> None:
    candidate = _candidate_result()
    assert candidate.plan is not None
    planner = SequencePlanner(
        (
            PlannerOutput(result=candidate),
            PlannerOutput(result=PlannerResult(continue_execution=True)),
        )
    )
    application = _application(planner, db_session)

    asyncio.run(application.submit_message("Investigate churn."))
    continued = asyncio.run(application.submit_message("Proceed with that plan."))

    assert PlanRepository(db_session).get_by_id(candidate.plan.plan_id) == candidate.plan
    assert (
        ActivePlanRepository(db_session).get_by_objective_id(candidate.plan.objective.objective_id)
        == candidate.plan
    )
    assert application.session_frame.objective == candidate.plan.objective
    assert application.session_frame.tasks == candidate.tasks
    assert planner.contexts[1].pending_plan == candidate.plan
    assert planner.contexts[1].active_plan is None
    assert application._pending_plan is None
    assert application._pending_tasks == ()
    assert continued.content == "The current Plan should continue execution."


def test_admitted_different_objective_does_not_switch_existing_session_frame(
    db_session: Session,
) -> None:
    candidate = _candidate_result()
    assert candidate.plan is not None
    planner = SequencePlanner(
        (
            PlannerOutput(result=candidate),
            PlannerOutput(result=PlannerResult(continue_execution=True)),
        )
    )
    application = _application(planner, db_session)
    existing = Objective(text="Existing Objective.")
    application.session_frame = application.session_frame.set_objective(existing)

    asyncio.run(application.submit_message("Propose a different scope."))
    asyncio.run(application.submit_message("Proceed with that proposal."))

    assert application.session_frame.objective == existing
    assert (
        ActivePlanRepository(db_session).get_by_objective_id(candidate.plan.objective.objective_id)
        == candidate.plan
    )


def test_continuation_with_only_active_plan_remains_valid_without_execution(
    db_session: Session,
) -> None:
    candidate = _candidate_result()
    assert candidate.plan is not None
    planner = SequencePlanner(
        (
            PlannerOutput(result=candidate),
            PlannerOutput(result=PlannerResult(continue_execution=True)),
            PlannerOutput(result=PlannerResult(continue_execution=True)),
        )
    )
    application = _application(planner, db_session)

    asyncio.run(application.submit_message("Investigate churn."))
    asyncio.run(application.submit_message("Proceed."))
    continued = asyncio.run(application.submit_message("Continue active work."))

    assert planner.contexts[2].pending_plan is None
    assert planner.contexts[2].active_plan == candidate.plan
    assert continued.content == "The current Plan should continue execution."


def test_pending_candidate_takes_precedence_over_existing_active_plan(
    db_session: Session,
) -> None:
    objective = Objective(text="Understand customer churn.")
    first = _candidate_result(objective=objective)
    successor = _candidate_result(
        objective=objective,
        instruction="Profile enterprise churn labels.",
    )
    assert first.plan is not None
    assert successor.plan is not None
    planner = SequencePlanner(
        (
            PlannerOutput(result=first),
            PlannerOutput(result=PlannerResult(continue_execution=True)),
            PlannerOutput(result=successor),
            PlannerOutput(result=PlannerResult(continue_execution=True)),
        )
    )
    application = _application(planner, db_session)

    asyncio.run(application.submit_message("Investigate churn."))
    asyncio.run(application.submit_message("Proceed."))
    asyncio.run(application.submit_message("Focus on enterprise customers."))
    asyncio.run(application.submit_message("Proceed with the revised plan."))

    assert planner.contexts[3].pending_plan == successor.plan
    assert planner.contexts[3].active_plan == first.plan
    assert PlanRepository(db_session).get_by_id(first.plan.plan_id) == first.plan
    assert PlanRepository(db_session).get_by_id(successor.plan.plan_id) == successor.plan
    assert ActivePlanRepository(db_session).get_by_objective_id(
        objective.objective_id
    ) == successor.plan


def test_continuation_without_pending_or_active_plan_fails_closed(
    db_session: Session,
) -> None:
    planner = SequencePlanner((PlannerOutput(result=PlannerResult(continue_execution=True)),))
    application = _application(planner, db_session)

    with pytest.raises(ValueError, match="pending or active Plan"):
        asyncio.run(application.submit_message("Continue."))


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
        session=db_session,
    )
    original_frame = application.session_frame

    response = asyncio.run(application.submit_message("/skill use planner review"))

    workspace.add_worker_skill.assert_called_once_with("planner", "review")
    agent_factory.reload_tooling.assert_called_once_with()
    planner.reload.assert_awaited_once_with(
        model_config=None,
        agent_instruction=None,
        recreate_agent=True,
    )
    planner.run.assert_not_called()
    assert application.session_frame is original_frame
    assert response.content == "Assigned 'review' to 'planner'."
