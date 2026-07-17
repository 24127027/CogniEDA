from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

import pytest
from sqlmodel import select

from agents.planner.agent import Planner
from agents.planner.types import (
    ChildTaskProposalDraft,
    Context,
    PlannerDecision,
    TaskDecompositionDraft,
)
from application.orchestrator.planner_commit import commit_planner_operations
from db.models import PlannerOperationRecord
from repositories import TaskRepository
from schemas.artifacts import Task
from schemas.enums import (
    PlannerOperationApprovalState,
    PlannerOperationType,
    TaskKind,
    TaskLifecycleState,
)


class FixedTaskDecompositionModel:
    """Return only non-executable children and retain the prompt for assertions."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def draft(self, prompt: str) -> TaskDecompositionDraft:
        self.prompts.append(prompt)
        return TaskDecompositionDraft(
            child_task_proposals=[
                ChildTaskProposalDraft(
                    title="Inventory data inputs",
                    description="List the source fields needed before analysis.",
                ),
                ChildTaskProposalDraft(
                    title="Review stakeholder constraints",
                    description="Confirm the operational limits for the investigation.",
                    task_kind=TaskKind.REVIEW,
                ),
            ]
        )


def _context(db_session, model: FixedTaskDecompositionModel) -> Context:
    return Context(
        database_url=str(db_session.get_bind().url),
        session_id="decomposition-session",
        task_decomposition_model=model,
    )


def test_decomposition_is_approval_gated_and_children_are_non_executable(db_session) -> None:
    parent = TaskRepository(db_session).create(
        Task(title="Investigate churn", description="Split this investigation into bounded work.")
    )
    model = FixedTaskDecompositionModel()
    context = _context(db_session, model)
    planner = Planner(database_url=context.database_url)

    proposed = asyncio.run(planner.run(f"/decompose {parent.task_id}", context)).payload

    assert proposed.pending_interaction is not None
    assert proposed.pending_interaction.kind == "planner_operation_approval"
    assert proposed.committed_operation_ids == []
    assert TaskRepository(db_session).list(parent_task_id=parent.task_id) == []
    assert len(proposed.planner_operations) == 2
    for operation in proposed.planner_operations:
        assert operation.operation_type == PlannerOperationType.CREATE_TASK
        assert operation.payload["parent_task_id"] == str(parent.task_id)
        assert operation.payload["lifecycle_state"] == TaskLifecycleState.PROPOSED.value
        assert operation.payload["task_kind"] in {TaskKind.ORGANIZING.value, TaskKind.REVIEW.value}
        assert "profile_id" not in operation.payload
        assert "variables" not in operation.payload
        assert "evidence_expectation" not in operation.payload
    assert model.prompts
    assert str(parent.task_id) not in model.prompts[0]

    wrong_approval = asyncio.run(
        planner.run(
            "/approve",
            context,
            decision=PlannerDecision(
                action="approve",
                proposal_id="different-proposal",
                selected_ids=proposed.pending_interaction.operation_ids,
            ),
        )
    ).payload
    assert wrong_approval.committed_operation_ids == []
    assert TaskRepository(db_session).list(parent_task_id=parent.task_id) == []

    approved = asyncio.run(
        planner.run(
            "/approve",
            context,
            decision=PlannerDecision(
                action="approve",
                proposal_id=proposed.pending_interaction.proposal_id,
                selected_ids=proposed.pending_interaction.operation_ids,
            ),
        )
    ).payload

    assert approved.commit_result is not None
    assert approved.commit_result.succeeded
    children = TaskRepository(db_session).list(parent_task_id=parent.task_id)
    assert len(children) == 2
    assert {child.lifecycle_state for child in children} == {TaskLifecycleState.PROPOSED}
    assert {child.task_kind for child in children} == {TaskKind.ORGANIZING, TaskKind.REVIEW}
    assert all(child.can_generate_hypothesis() is False for child in children)


def test_decomposition_rejects_unknown_or_malformed_parent_without_operations(db_session) -> None:
    planner = Planner(database_url=str(db_session.get_bind().url))
    context = _context(db_session, FixedTaskDecompositionModel())

    malformed = asyncio.run(planner.run("/decompose not-a-uuid", context)).payload
    unknown = asyncio.run(planner.run(f"/decompose {uuid4()}", context)).payload

    assert malformed.controlled_error is not None
    assert malformed.controlled_error.code == "malformed_decomposition_parent"
    assert unknown.controlled_error is not None
    assert unknown.controlled_error.code == "unknown_decomposition_parent"
    assert list(db_session.exec(select(PlannerOperationRecord)).all()) == []


def test_decomposition_batch_rolls_back_when_a_parent_is_invalid(db_session) -> None:
    parent = TaskRepository(db_session).create(Task(title="Parent", description="Parent task"))
    model = FixedTaskDecompositionModel()
    context = _context(db_session, model)
    proposed = asyncio.run(
        Planner(database_url=context.database_url).run(f"/decompose {parent.task_id}", context)
    ).payload
    assert proposed.pending_interaction is not None

    records = list(db_session.exec(select(PlannerOperationRecord)).all())
    assert len(records) == 2
    records[-1].payload = {**records[-1].payload, "parent_task_id": str(uuid4())}
    for record in records:
        record.approval_state = PlannerOperationApprovalState.APPROVED
        db_session.add(record)
    db_session.commit()

    result = commit_planner_operations(
        db_session,
        session_id="decomposition-session",
        operation_ids=[
            UUID(operation_id) for operation_id in proposed.pending_interaction.operation_ids
        ],
    )

    assert result.succeeded is False
    assert TaskRepository(db_session).list(parent_task_id=parent.task_id) == []


def test_child_task_draft_cannot_be_analytical() -> None:
    with pytest.raises(ValueError):
        ChildTaskProposalDraft(
            title="Invalid analytical child",
            description="This must be rejected at the typed draft boundary.",
            task_kind=TaskKind.ANALYTICAL,
        )
