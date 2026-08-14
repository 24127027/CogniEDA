from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import pytest
from pydantic_ai.messages import ModelMessage, ModelRequest, UserPromptPart
from sqlmodel import Session

from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.contracts import PlannerResult
from cognieda.agents.planner.dependencies import PlannerDeps
from cognieda.application.ports import ModelConfig
from cognieda.execution import ExecutorDispatcher, ExecutorRegistry
from cognieda.infrastructure.persistence.models import ActivePlanRecord
from cognieda.infrastructure.persistence.repositories import PlanRepository
from cognieda.runtime.application import Application
from cognieda.runtime.workspace import Workspace
from cognieda.schemas import Objective, Plan, PlanTaskBinding, SessionFrame, Task, TaskKind


@dataclass
class FakeRunResult:
    output: object
    messages: tuple[ModelMessage, ...]

    def all_messages(self) -> list[ModelMessage]:
        return list(self.messages)


class QueueAgent:
    def __init__(self, outputs: list[PlannerResult]) -> None:
        self.outputs = iter(outputs)
        self.call_count = 0

    async def run(self, _prompt: str, **kwargs: object) -> FakeRunResult:
        self.call_count += 1
        history = tuple(kwargs.get("message_history", ()))
        return FakeRunResult(
            next(self.outputs),
            (*history,
                ModelRequest(
                    parts=[UserPromptPart(content=f"planner call {self.call_count}")]
                ),
            ),
        )


class QueueFactory:
    def __init__(self, agent: QueueAgent) -> None:
        self.agent = agent

    def create_agent(self, **_kwargs: object) -> QueueAgent:
        return self.agent

    def reload_tooling(self) -> None:
        pass


def _candidate(label: str) -> PlannerResult:
    objective = Objective(text=f"Investigate {label} retention.")
    task = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction=f"Profile {label} retention data.",
    )
    plan = Plan.create(
        objective=objective,
        task_bindings=(PlanTaskBinding(task_id=task.task_id, order_rank=0),),
        tasks=(task,),
    )
    return PlannerResult(
        plan=plan,
        tasks=(task,),
        response=f"Review the {label} Plan.",
    )


def _application(
    tmp_path: Path,
    db_session: Session,
    outputs: list[PlannerResult],
) -> tuple[Application, QueueAgent]:
    agent = QueueAgent(outputs)
    factory = QueueFactory(agent)
    dispatcher = ExecutorDispatcher(ExecutorRegistry())
    planner = Planner(
        PlannerDeps(dispatcher),
        agent_factory=factory,  # type: ignore[arg-type]
        model_config=ModelConfig(provider="openai", model_name="test", api_key="key"),
    )
    return (
        Application(
            workspace=Workspace.open(tmp_path),
            planner_agent=planner,
            dispatcher=dispatcher,
            agent_factory=factory,  # type: ignore[arg-type]
            session=db_session,
        ),
        agent,
    )


def test_application_pauses_before_persistence_and_exact_approval_commits(
    tmp_path: Path,
    db_session: Session,
) -> None:
    candidate = _candidate("approved")
    application, agent = _application(
        tmp_path,
        db_session,
        [candidate, PlannerResult(response="Execution complete.")],
    )
    plan = candidate.plan
    assert plan is not None

    proposed = asyncio.run(application.submit_message("Investigate retention"))

    assert str(plan.plan_id) in proposed.content
    assert application._pending_plan == plan
    assert PlanRepository(db_session).get_by_id(plan.plan_id) is None
    assert application.conversation_history.turns == ()

    completed = asyncio.run(application.submit_message(f"/approve {plan.plan_id}"))

    assert completed.content == "Execution complete."
    assert PlanRepository(db_session).get_by_id(plan.plan_id) == plan
    active = db_session.get(ActivePlanRecord, plan.objective.objective_id)
    assert active is not None and active.plan_id == plan.plan_id
    assert application.session_frame.objective == plan.objective
    assert application.session_frame.tasks == candidate.tasks
    assert len(application.conversation_history.turns) == 1
    assert len(application.conversation_history.turns[0].messages) == 2
    assert agent.call_count == 2


def test_rejection_persists_nothing_and_revised_plan_requires_new_review(
    tmp_path: Path,
    db_session: Session,
) -> None:
    original = _candidate("original")
    replacement = _candidate("replacement")
    application, _ = _application(tmp_path, db_session, [original, replacement])
    original_plan = original.plan
    replacement_plan = replacement.plan
    assert original_plan is not None and replacement_plan is not None

    asyncio.run(application.submit_message("Investigate retention"))
    revised = asyncio.run(
        application.submit_message(
            f"/revise {original_plan.plan_id} Narrow the population."
        )
    )

    assert str(replacement_plan.plan_id) in revised.content
    assert PlanRepository(db_session).get_by_id(original_plan.plan_id) is None
    assert PlanRepository(db_session).get_by_id(replacement_plan.plan_id) is None
    assert application._pending_plan == replacement_plan
    assert application.conversation_history.turns == ()


def test_execute_replan_routes_to_plan_and_interrupts_again(
    tmp_path: Path,
    db_session: Session,
) -> None:
    original = _candidate("original")
    replacement = _candidate("replacement")
    application, _ = _application(
        tmp_path,
        db_session,
        [
            original,
            PlannerResult(continue_execution=True),
            replacement,
        ],
    )
    original_plan = original.plan
    replacement_plan = replacement.plan
    assert original_plan is not None and replacement_plan is not None

    asyncio.run(application.submit_message("Investigate retention"))
    replanned = asyncio.run(
        application.submit_message(f"/approve {original_plan.plan_id}")
    )

    assert str(replacement_plan.plan_id) in replanned.content
    assert PlanRepository(db_session).get_by_id(original_plan.plan_id) == original_plan
    assert PlanRepository(db_session).get_by_id(replacement_plan.plan_id) is None
    assert application._pending_plan == replacement_plan
    assert application.conversation_history.turns == ()


def test_wrong_plan_identity_fails_closed_without_resuming(
    tmp_path: Path,
    db_session: Session,
) -> None:
    candidate = _candidate("exact")
    application, agent = _application(tmp_path, db_session, [candidate])
    asyncio.run(application.submit_message("Investigate retention"))

    response = asyncio.run(
        application.submit_message("/approve 00000000-0000-0000-0000-000000000000")
    )

    assert "No pending candidate matches" in response.content
    assert agent.call_count == 1


def test_approved_new_objective_replaces_only_an_empty_old_objective_scope(
    tmp_path: Path,
    db_session: Session,
) -> None:
    candidate = _candidate("new")
    application, _ = _application(tmp_path, db_session, [candidate])
    old_objective = Objective(text="Old framing without retained scoped work")
    application.session_frame = SessionFrame(objective=old_objective)
    assert candidate.plan is not None

    successor = application._successor_for_approved_plan(candidate.plan, candidate.tasks)

    assert successor.objective == candidate.plan.objective
    assert successor.tasks == candidate.tasks


def test_approved_new_objective_fails_closed_when_old_scoped_work_is_retained(
    tmp_path: Path,
    db_session: Session,
) -> None:
    candidate = _candidate("new")
    application, _ = _application(tmp_path, db_session, [candidate])
    old_objective = Objective(text="Old framing with retained work")
    old_task = Task(
        objective_id=old_objective.objective_id,
        kind=TaskKind.DATA,
        instruction="Retained old-Objective work",
    )
    application.session_frame = SessionFrame(
        objective=old_objective,
        tasks=(old_task,),
    )
    assert candidate.plan is not None

    with pytest.raises(ValueError, match="canonical successor contract"):
        application._successor_for_approved_plan(candidate.plan, candidate.tasks)
