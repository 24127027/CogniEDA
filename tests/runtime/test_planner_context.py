from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from cognieda.runtime.conversation import ConversationHistory
from cognieda.runtime.planner_context import build_planner_context
from cognieda.schemas import (
    Assumption,
    DataProfile,
    Discovery,
    DiscoveryClaim,
    Evidence,
    EvidenceProvenance,
    Objective,
    Plan,
    SessionFrame,
    Task,
    ValidityBasis,
)
from cognieda.schemas.enums import DiscoveryEpistemicStatus, TaskKind, TaskStatus


def _full_frame() -> SessionFrame:
    objective = Objective(text="Understand dataset completeness.")
    assumption = Assumption(text="Rows represent independent observations.")
    task = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="Count rows.",
        status=TaskStatus.COMPLETED,
    )
    profile = DataProfile(row_count=42, column_count=0, columns=())
    evidence = Evidence(
        task_id=task.task_id,
        data_profile_id=profile.data_profile_id,
        content={"row_count": 42},
        provenance=EvidenceProvenance(
            producer_role="data_explorer",
            work_reference="work:count-rows",
            dataset_reference="dataset:v1",
            data_profile_id=profile.data_profile_id,
        ),
    )
    hypothesis_id = uuid4()
    discovery = Discovery(
        hypothesis_id=hypothesis_id,
        evidence_ids=[evidence.evidence_id],
        claim=DiscoveryClaim(
            statement="The admitted dataset contains 42 rows.",
            scope="dataset:v1",
        ),
        epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
        scope="dataset:v1",
        validity_basis=ValidityBasis(
            data_profile_id=profile.data_profile_id,
            analysis_frame_refs=["analysis:row-count"],
            hypothesis_id=hypothesis_id,
            evidence_ids=[evidence.evidence_id],
            method="row count",
            decision_rule="Support when the admitted count is 42.",
        ),
    )
    return SessionFrame(
        objective=objective,
        assumptions=(assumption,),
        tasks=(task,),
        evidences=(evidence,),
        discoveries=(discovery,),
        data_profile=profile,
    )


def test_builder_exactly_materializes_every_readable_session_frame_member() -> None:
    frame = _full_frame()
    history = ConversationHistory()

    context = build_planner_context(frame, history)

    assert context.active_plan is None
    assert context.objective == frame.objective
    assert context.assumptions == frame.assumptions
    assert context.tasks == frame.tasks
    assert context.evidences == frame.evidences
    assert context.discoveries == frame.discoveries
    assert context.data_profile == frame.data_profile
    assert context.conversation_history == history
    with pytest.raises(ValidationError, match="frozen"):
        context.tasks = ()


def test_session_frame_retains_discovery_membership_immutably() -> None:
    frame = _full_frame()
    discovery = frame.discoveries[0]
    empty = SessionFrame()

    successor = empty.add_discovery(discovery)

    assert empty.discoveries == ()
    assert successor.discoveries == (discovery,)
    with pytest.raises(ValidationError, match="duplicate Discovery"):
        SessionFrame(discoveries=(discovery, discovery))


def test_builder_materializes_exact_active_plan_for_current_objective() -> None:
    frame = _full_frame()
    assert frame.objective is not None
    plan = Plan.create(
        objective=frame.objective,
        assumptions=frame.assumptions,
        task_ids=(task.task_id for task in frame.tasks),
        tasks=frame.tasks,
    )

    context = build_planner_context(
        frame,
        ConversationHistory(),
        active_plan=plan,
    )

    assert context.active_plan is plan


def test_builder_rejects_active_plan_for_different_objective() -> None:
    frame = _full_frame()
    other = Objective(text="Different Objective.")
    plan = Plan.create(objective=other, task_ids=(), tasks=())

    with pytest.raises(ValueError, match="exact SessionFrame Objective"):
        build_planner_context(
            frame,
            ConversationHistory(),
            active_plan=plan,
        )
