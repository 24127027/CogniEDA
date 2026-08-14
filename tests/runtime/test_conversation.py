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
from cognieda.application.services import PlanAdmissionService
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
        self.message_histories: list[tuple[ModelMessage, ...]] = []

    async def run(
        self,
        request: str,
        *,
        context: PlannerContext,
        message_history: list[ModelMessage] | None = None,
    ) -> PlannerOutput:
        self.requests.append(request)
        self.contexts.append(context)
        self.message_histories.append(tuple(message_history or ()))
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
    assert not hasattr(Application, "_apply_planner_result")


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


def test_candidate_is_invocation_output_only_without_authoritative_writes(
    db_session: Session,
) -> None:
    first_messages = _messages("Investigate churn.", "Proposed a plan.")
    candidate = _candidate_result()
    assert candidate.plan is not None
    planner = SequencePlanner((PlannerOutput(result=candidate, messages=first_messages),))
    application = _application(planner, db_session)

    first = asyncio.run(application.submit_message("Investigate churn."))

    assert first.content == "I propose a bounded investigation."
    assert not hasattr(application, "_pending_plan")
    assert not hasattr(application, "_pending_tasks")
    assert application.session_frame.objective is None
    assert application.session_frame.tasks == ()
    assert len(application.conversation_history.turns) == 1
    assert tuple(type(planner.contexts[0]).model_fields) == (
        "active_plan",
        "objective",
        "assumptions",
        "tasks",
        "evidences",
        "discoveries",
        "data_profile",
    )
    assert planner.message_histories == [()]
    assert ObjectiveRepository(db_session).get_by_id(candidate.plan.objective.objective_id) is None
    assert TaskRepository(db_session).get_by_id(candidate.tasks[0].task_id) is None
    assert PlanRepository(db_session).get_by_id(candidate.plan.plan_id) is None
    assert (
        ActivePlanRepository(db_session).get_by_objective_id(candidate.plan.objective.objective_id)
        is None
    )


def test_conversation_history_is_passed_separately_from_planner_context(
    db_session: Session,
) -> None:
    first_messages = _messages("First request", "First response")
    second_messages = _messages("Second request", "Second response")
    planner = SequencePlanner(
        (
            PlannerOutput(
                result=PlannerResult(response="First response"),
                messages=first_messages,
            ),
            PlannerOutput(
                result=PlannerResult(response="Second response"),
                messages=second_messages,
            ),
        )
    )
    application = _application(planner, db_session)

    asyncio.run(application.submit_message("First request"))
    asyncio.run(application.submit_message("Second request"))

    assert planner.message_histories == [(), first_messages]
    assert all(
        "conversation_history" not in type(context).model_fields for context in planner.contexts
    )
    assert application.conversation_history.model_messages() == [
        *first_messages,
        *second_messages,
    ]


def test_followup_cannot_admit_an_invocation_local_candidate(
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

    assert continued.content == "The current Plan should continue execution."
    assert all(context.active_plan is None for context in planner.contexts)
    assert PlanRepository(db_session).get_by_id(candidate.plan.plan_id) is None
    assert ObjectiveRepository(db_session).get_by_id(candidate.plan.objective.objective_id) is None
    assert TaskRepository(db_session).get_by_id(candidate.tasks[0].task_id) is None
    assert (
        ActivePlanRepository(db_session).get_by_objective_id(candidate.plan.objective.objective_id)
        is None
    )


def test_active_plan_materializes_only_from_authoritative_repository_state(
    db_session: Session,
) -> None:
    candidate = _candidate_result()
    assert candidate.plan is not None
    admitted = PlanAdmissionService(db_session).admit(candidate.plan, tasks=candidate.tasks)
    planner = SequencePlanner((PlannerOutput(result=PlannerResult(continue_execution=True)),))
    application = _application(planner, db_session)
    application.session_frame = application.session_frame.set_objective(candidate.plan.objective)

    continued = asyncio.run(application.submit_message("Continue active work."))

    assert planner.contexts[0].active_plan == admitted
    assert planner.contexts[0].tasks == ()
    assert PlanRepository(db_session).get_by_id(admitted.plan_id) == admitted
    assert (
        ActivePlanRepository(db_session).get_by_objective_id(admitted.objective.objective_id)
        == admitted
    )
    assert continued.content == "The current Plan should continue execution."


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
