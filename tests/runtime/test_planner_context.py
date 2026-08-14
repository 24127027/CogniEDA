from __future__ import annotations

import inspect
from uuid import uuid4

import pytest
from pydantic import ValidationError

from cognieda.agents.planner.context import PlannerContext
from cognieda.runtime.conversation import ConversationHistory
from cognieda.runtime.planner_context import build_planner_context
from cognieda.schemas.artifacts import (
    Assumption,
    DataProfile,
    Discovery,
    Evidence,
    Objective,
    SessionFrame,
    Task,
)
from cognieda.schemas.common import DiscoveryClaim, EvidenceProvenance, ValidityBasis
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
        claim=DiscoveryClaim(statement="There are 42 rows.", scope="dataset:v1"),
        epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
        scope="dataset:v1",
        validity_basis=ValidityBasis(
            data_profile_id=profile.data_profile_id,
            analysis_frame_refs=["analysis:count"],
            hypothesis_id=hypothesis_id,
            evidence_ids=[evidence.evidence_id],
            method="row count",
            decision_rule="Report exact count.",
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


def test_builder_exactly_materializes_every_retained_session_frame_member() -> None:
    frame = _full_frame()

    history = ConversationHistory()
    context = build_planner_context(frame, history)

    assert context.objective == frame.objective
    assert context.assumptions == frame.assumptions
    assert context.tasks == frame.tasks
    assert context.evidences == frame.evidences
    assert context.discoveries == frame.discoveries
    assert context.data_profile == frame.data_profile
    assert context.conversation_history == history
    with pytest.raises(ValidationError, match="frozen"):
        context.tasks = ()


def test_planner_context_has_exact_readable_membership() -> None:
    assert set(PlannerContext.model_fields) == {
        "active_plan",
        "objective",
        "assumptions",
        "tasks",
        "evidences",
        "discoveries",
        "data_profile",
        "conversation_history",
    }
    assert set(inspect.signature(build_planner_context).parameters) == {
        "session_frame",
        "conversation_history",
        "active_plan",
    }

