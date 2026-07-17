"""Public Planner characterization for governed Objective lifecycle batches."""

from __future__ import annotations

import asyncio
import re

import pytest

from agents.planner.agent import Planner
from agents.planner.nodes import ObjectiveManagementDraft
from agents.planner.types import (
    Context,
    ObjectiveCreateDraft,
    ObjectiveUpdateDraft,
    PlannerDecision,
)
from repositories.objective_repository import ObjectiveRepository
from repositories.objective_revision_repository import ObjectiveRevisionRepository
from repositories.planner_operation_repository import PlannerOperationRepository
from repositories.session_frame_repository import SessionFrameRepository
from schemas.enums import ObjectiveStatus, PlannerOperationApprovalState


class CreateObjectiveModel:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def draft(self, prompt: str) -> ObjectiveManagementDraft:
        self.prompts.append(prompt)
        return ObjectiveManagementDraft(
            objective_create_payloads=[
                ObjectiveCreateDraft(
                    title="Churn Objective",
                    statement="Understand governed churn drivers.",
                )
            ]
        )


class UpdateCurrentObjectiveModel:
    def __init__(self, status: ObjectiveStatus) -> None:
        self.status = status
        self.prompts: list[str] = []

    def draft(self, prompt: str) -> ObjectiveManagementDraft:
        self.prompts.append(prompt)
        match = re.search(r"Current ACTIVE reference: (objective:[^\n]+)", prompt)
        if match is None:
            raise ValueError("No current Objective reference was supplied.")
        return ObjectiveManagementDraft(
            objective_update_payloads=[
                ObjectiveUpdateDraft(
                    objective_ref=match.group(1),
                    status=self.status,
                    revision_reason="User explicitly accepted Objective completion.",
                )
            ]
        )


class SwitchCurrentObjectiveModel:
    def draft(self, prompt: str) -> ObjectiveManagementDraft:
        match = re.search(r"Current ACTIVE reference: (objective:[^\n]+)", prompt)
        if match is None:
            raise ValueError("No current Objective reference was supplied.")
        return ObjectiveManagementDraft(
            objective_update_payloads=[
                ObjectiveUpdateDraft(
                    objective_ref=match.group(1),
                    status=ObjectiveStatus.ARCHIVED,
                    revision_reason="User explicitly switched research direction.",
                )
            ],
            objective_create_payloads=[
                ObjectiveCreateDraft(
                    title="Replacement Objective",
                    statement="Investigate the replacement direction.",
                )
            ],
        )


def _run(
    database_url: str,
    query: str,
    context: Context,
    decision: PlannerDecision | None = None,
):
    return asyncio.run(
        Planner(database_url=database_url).run(
            query,
            context,
            decision=decision,
        )
    ).payload


def _approve(database_url: str, session_id: str, interaction):
    return _run(
        database_url,
        "/approve",
        Context(session_id=session_id),
        PlannerDecision(
            action="approve",
            proposal_id=interaction.proposal_id,
            selected_ids=interaction.operation_ids,
        ),
    )


def test_public_objective_create_and_completion_append_successor_frames_and_revision(
    db_session,
) -> None:
    database_url = str(db_session.get_bind().url)
    session_id = "objective-public-session"
    create_model = CreateObjectiveModel()
    proposed = _run(
        database_url,
        "/objective create the initial research intent",
        Context(
            session_id=session_id,
            objective_management_model=create_model,
        ),
    )

    assert len(create_model.prompts) == 1
    assert "Current ACTIVE reference: None" in create_model.prompts[0]
    assert proposed.pending_interaction.kind == "planner_operation_approval"
    assert len(proposed.pending_interaction.operation_ids) == 2
    assert proposed.committed_operation_ids == []
    assert ObjectiveRepository(db_session).get_active() is None

    created = _approve(database_url, session_id, proposed.pending_interaction)
    active = ObjectiveRepository(db_session).get_active()
    first_frame = SessionFrameRepository(db_session).get_latest()
    assert created.commit_result.succeeded
    assert created.committed_operation_ids == created.commit_result.committed_operation_ids
    assert created.session_frame_id == first_frame.session_frame_id
    assert active is not None and active.status == ObjectiveStatus.ACTIVE
    assert first_frame.objective_snapshot == active.statement
    assert ObjectiveRevisionRepository(db_session).list_for_objective(active.objective_id) == []

    complete_model = UpdateCurrentObjectiveModel(ObjectiveStatus.COMPLETED)
    completion_proposal = _run(
        database_url,
        "/objective complete the current objective",
        Context(
            session_id=session_id,
            objective_management_model=complete_model,
        ),
    )
    assert len(complete_model.prompts) == 1
    assert "Current ACTIVE reference: objective:" in complete_model.prompts[0]
    completed = _approve(database_url, session_id, completion_proposal.pending_interaction)

    final_objective = ObjectiveRepository(db_session).get_by_id(active.objective_id)
    successor = SessionFrameRepository(db_session).get_latest()
    revisions = ObjectiveRevisionRepository(db_session).list_for_objective(active.objective_id)
    assert completed.commit_result.succeeded
    assert ObjectiveRepository(db_session).get_active() is None
    assert final_objective.status == ObjectiveStatus.COMPLETED
    assert successor.parent_session_frame_id == first_frame.session_frame_id
    assert successor.objective_summary == "Objective is completed: Churn Objective"
    assert len(revisions) == 1
    assert revisions[0].previous_status == ObjectiveStatus.ACTIVE
    assert revisions[0].new_status == ObjectiveStatus.COMPLETED
    assert revisions[0].user_decision_id is None
    assert revisions[0].actor == "user-approved-planner-operation"


@pytest.mark.parametrize("action", ["cancel", "revise"])
def test_public_objective_cancellation_and_revision_do_not_mutate(
    db_session,
    action: str,
) -> None:
    database_url = str(db_session.get_bind().url)
    session_id = f"objective-{action}-session"
    proposed = _run(
        database_url,
        "/objective create intent",
        Context(
            session_id=session_id,
            objective_management_model=CreateObjectiveModel(),
        ),
    )
    result = _run(
        database_url,
        f"/{action}",
        Context(session_id=session_id),
        PlannerDecision(
            action=action,
            proposal_id=proposed.pending_interaction.proposal_id,
            selected_ids=proposed.pending_interaction.operation_ids,
        ),
    )

    assert result.committed_operation_ids == []
    assert ObjectiveRepository(db_session).list() == []
    assert SessionFrameRepository(db_session).list() == []
    assert all(
        operation.approval_state == PlannerOperationApprovalState.REJECTED
        for operation in PlannerOperationRepository(db_session).list(session_id=session_id)
    )


def test_public_active_switch_is_one_approved_atomic_batch(db_session) -> None:
    database_url = str(db_session.get_bind().url)
    session_id = "objective-switch-session"
    initial = _run(
        database_url,
        "/objective create initial intent",
        Context(
            session_id=session_id,
            objective_management_model=CreateObjectiveModel(),
        ),
    )
    _approve(database_url, session_id, initial.pending_interaction)
    previous = ObjectiveRepository(db_session).get_active()
    previous_frame = SessionFrameRepository(db_session).get_latest()

    proposed = _run(
        database_url,
        "/objective switch research direction",
        Context(
            session_id=session_id,
            objective_management_model=SwitchCurrentObjectiveModel(),
        ),
    )
    assert len(proposed.pending_interaction.operation_ids) == 3
    committed = _approve(database_url, session_id, proposed.pending_interaction)

    current = ObjectiveRepository(db_session).get_active()
    successor = SessionFrameRepository(db_session).get_latest()
    assert committed.commit_result.succeeded
    assert current.title == "Replacement Objective"
    assert ObjectiveRepository(db_session).get_by_id(previous.objective_id).status == (
        ObjectiveStatus.ARCHIVED
    )
    assert successor.parent_session_frame_id == previous_frame.session_frame_id
    revisions = ObjectiveRevisionRepository(db_session).list_for_objective(
        previous.objective_id
    )
    assert len(revisions) == 1
    assert revisions[0].new_status == ObjectiveStatus.ARCHIVED


def test_public_objective_approval_rejects_tamper_wrong_session_reorder_and_replay(
    db_session,
) -> None:
    database_url = str(db_session.get_bind().url)
    session_id = "objective-authority-session"
    proposed = _run(
        database_url,
        "/objective create intent",
        Context(
            session_id=session_id,
            objective_management_model=CreateObjectiveModel(),
        ),
    )
    interaction = proposed.pending_interaction

    tampered = _run(
        database_url,
        "/approve",
        Context(session_id=session_id),
        PlannerDecision(
            action="approve",
            proposal_id="tampered-fingerprint",
            selected_ids=interaction.operation_ids,
        ),
    )
    assert tampered.committed_operation_ids == []
    assert ObjectiveRepository(db_session).list() == []

    wrong_session = _run(
        database_url,
        "/approve",
        Context(session_id="wrong-objective-session"),
        PlannerDecision(
            action="approve",
            proposal_id=interaction.proposal_id,
            selected_ids=interaction.operation_ids,
        ),
    )
    assert wrong_session.controlled_error.code == "invalid_planner_operation_proposal"
    assert ObjectiveRepository(db_session).list() == []

    reordered = _run(
        database_url,
        "/approve",
        Context(session_id=session_id),
        PlannerDecision(
            action="approve",
            proposal_id=interaction.proposal_id,
            selected_ids=list(reversed(interaction.operation_ids)),
        ),
    )
    assert reordered.committed_operation_ids == []
    assert ObjectiveRepository(db_session).list() == []

    committed = _approve(database_url, session_id, interaction)
    assert committed.commit_result.succeeded
    assert ObjectiveRepository(db_session).get_active() is not None

    replay = _approve(database_url, session_id, interaction)
    assert replay.controlled_error.code == "invalid_planner_operation_proposal"
    assert len(ObjectiveRepository(db_session).list()) == 1
