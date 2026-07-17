from __future__ import annotations

import asyncio
from typing import cast
from uuid import UUID

import pytest
from langgraph.runtime import Runtime
from pydantic_ai.messages import ModelRequest, UserPromptPart

from agents.planner.agent import Planner
from agents.planner.nodes import TaskManagementDraft, route_intent, understand_request
from agents.planner.types import (
    COMMAND_TO_INTENT,
    Context,
    PlannerDecision,
    RequestUnderstanding,
    RequestUnderstandingModel,
    State,
    TaskCreateDraft,
    parse_explicit_command,
)
from repositories import PlannerOperationRepository, TaskRepository
from schemas.enums import PlannerOperationApprovalState


class FakeRequestUnderstandingModel(RequestUnderstandingModel):
    def __init__(self, result: object) -> None:
        self.result = result
        self.prompts: list[str] = []

    def understand(self, prompt: str) -> RequestUnderstanding:
        self.prompts.append(prompt)
        return cast(RequestUnderstanding, self.result)


class FixedTaskManagementModel:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def draft(self, prompt: str) -> TaskManagementDraft:
        self.prompts.append(prompt)
        return TaskManagementDraft(
            task_create_payloads=[
                TaskCreateDraft(
                    title="Review missing values",
                    description="Inspect missing-value patterns before execution.",
                    variables=["monthly_spend"],
                    evidence_expectation="A missingness profile.",
                )
            ]
        )


def runtime_with(model: RequestUnderstandingModel | None = None) -> Runtime[Context]:
    return Runtime(context=Context(request_understanding_model=model))


@pytest.mark.parametrize(
    ("query", "intent", "request_text"),
    [
        ("/answer What was discovered?", "answer", "What was discovered?"),
        ("/manage_task create a profiling task", "manage_task", "create a profiling task"),
        ("   /objective refine the objective", "objective", "refine the objective"),
        ("/ANSWER What was discovered?", "answer", "What was discovered?"),
        ("/answer", "answer", ""),
    ],
)
def test_explicit_commands_bypass_the_model(
    query: str,
    intent: str,
    request_text: str,
) -> None:
    model = FakeRequestUnderstandingModel(
        RequestUnderstanding(intent="suggest", request_text="unexpected", source="llm")
    )

    result = understand_request(State(query=query), runtime_with(model))

    assert result.request_understanding == RequestUnderstanding(
        intent=intent,
        request_text=request_text,
        source="explicit_command",
        explicit_command=intent,
    )
    assert model.prompts == []


def test_parse_explicit_command_preserves_payload_and_normalizes_command() -> None:
    result = parse_explicit_command("  /MANAGE_TASK  retain   inner whitespace  ")

    assert result is not None
    assert result.command == "manage_task"
    assert result.original_command == "/MANAGE_TASK"
    assert result.request_text == "retain   inner whitespace"


def test_request_model_receives_only_the_latest_query() -> None:
    query = "Create a new task to inspect missing values."
    model = FakeRequestUnderstandingModel(
        RequestUnderstanding(
            intent="manage_task",
            request_text="inspect missing values",
            source="llm",
        )
    )

    result = understand_request(
        State(
            query=query,
            history=[ModelRequest(parts=[UserPromptPart(content="history-only-secret")])],
        ),
        runtime_with(model),
    )

    assert result.request_understanding is not None
    assert result.request_understanding.intent == "manage_task"
    assert len(model.prompts) == 1
    assert query in model.prompts[0]
    assert "history-only-secret" not in model.prompts[0]


def test_unknown_command_requires_correction_without_model_fallback() -> None:
    model = FakeRequestUnderstandingModel(
        RequestUnderstanding(intent="answer", request_text="unexpected", source="llm")
    )

    result = understand_request(State(query="/unknown remove everything"), runtime_with(model))

    understanding = result.request_understanding
    assert understanding is not None
    assert understanding.intent is None
    assert understanding.source == "invalid_command"
    assert understanding.requires_user_correction is True
    assert understanding.supported_commands == tuple(f"/{key}" for key in COMMAND_TO_INTENT)
    assert model.prompts == []
    assert route_intent(result, runtime_with(model)) == "invalid_request"


def test_task_proposal_commits_only_after_matching_approval(db_session) -> None:
    database_url = str(db_session.get_bind().url)
    context = Context(
        session_id="task-proposal-session",
        task_management_model=FixedTaskManagementModel(),
    )
    planner = Planner(database_url=database_url)

    first = asyncio.run(
        planner.run("/manage_task create a missing-value review task", context)
    ).payload

    assert first.pending_interaction is not None
    assert first.pending_interaction.kind == "planner_operation_approval"
    assert first.committed_operation_ids == []
    assert len(first.pending_interaction.operation_ids) == 1
    assert TaskRepository(db_session).list() == []

    operation_id = first.pending_interaction.operation_ids[0]
    persisted = PlannerOperationRepository(db_session).get_by_id(UUID(operation_id))
    assert persisted is not None
    assert persisted.approval_state == PlannerOperationApprovalState.PENDING
    assert persisted.target_object_id is None
    assert "task_id" not in persisted.payload

    tampered = asyncio.run(
        planner.run(
            "/approve",
            context,
            decision=PlannerDecision(
                action="approve",
                proposal_id="tampered-proposal",
                selected_ids=first.pending_interaction.operation_ids,
            ),
        )
    ).payload

    assert tampered.committed_operation_ids == []
    assert TaskRepository(db_session).list() == []

    approved = asyncio.run(
        planner.run(
            "/approve",
            context,
            decision=PlannerDecision(
                action="approve",
                proposal_id=first.pending_interaction.proposal_id,
                selected_ids=first.pending_interaction.operation_ids,
            ),
        )
    ).payload

    assert approved.commit_result is not None
    assert approved.commit_result.succeeded
    assert approved.committed_operation_ids == approved.commit_result.committed_operation_ids
    assert len(TaskRepository(db_session).list()) == 1

    replay = asyncio.run(
        planner.run(
            "/approve",
            context,
            decision=PlannerDecision(
                action="approve",
                proposal_id=first.pending_interaction.proposal_id,
                selected_ids=first.pending_interaction.operation_ids,
            ),
        )
    ).payload

    assert replay.controlled_error is not None
    assert replay.controlled_error.code == "invalid_planner_operation_proposal"
    assert len(TaskRepository(db_session).list()) == 1


def test_task_proposal_resume_rejects_wrong_session_and_missing_ids(db_session) -> None:
    database_url = str(db_session.get_bind().url)
    context = Context(
        session_id="task-proposal-session",
        task_management_model=FixedTaskManagementModel(),
    )
    planner = Planner(database_url=database_url)
    proposed = asyncio.run(planner.run("/manage_task create a review task", context)).payload

    assert proposed.pending_interaction is not None

    wrong_session = asyncio.run(
        planner.run(
            "/approve",
            Context(session_id="other-session"),
            decision=PlannerDecision(
                action="approve",
                proposal_id=proposed.pending_interaction.proposal_id,
                selected_ids=proposed.pending_interaction.operation_ids,
            ),
        )
    ).payload
    missing_ids = asyncio.run(
        planner.run(
            "/approve",
            context,
            decision=PlannerDecision(
                action="approve",
                proposal_id=proposed.pending_interaction.proposal_id,
            ),
        )
    ).payload

    assert wrong_session.controlled_error is not None
    assert wrong_session.controlled_error.code == "invalid_planner_operation_proposal"
    assert missing_ids.controlled_error is not None
    assert missing_ids.controlled_error.code == "planner_operation_resume_unavailable"
    assert TaskRepository(db_session).list() == []
