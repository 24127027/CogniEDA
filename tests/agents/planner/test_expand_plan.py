import re
from uuid import uuid4

import pytest
from langgraph.checkpoint.memory import MemorySaver

from agents.planner.graph import build_graph
from agents.planner.types import ChildTaskProposalDraft, Context, TaskDecompositionDraft
from application.orchestrator.planner_commit import commit_planner_operations
from db.models import (
    DataProfileRecord,
    DiscoveryRecord,
    HypothesisRecord,
    ObjectiveRecord,
    TaskRecord,
)
from repositories import DataProfileRepository, SessionFrameRepository, TaskRepository
from schemas.artifacts import DataProfile, SessionFrame, Task
from schemas.common import BaselineSummary, EvaluationThresholds, MethodParameter, SchemaSummary
from schemas.enums import (
    DataProfileLifecycleState,
    DataProfileMethod,
    DiscoveryEpistemicStatus,
    DiscoveryLifecycleState,
    PlannerOperationApprovalState,
    PlannerOperationType,
    TaskKind,
)
from schemas.planner_operations import PlannerOperation


class EmptyMotivationDecompositionModel:
    """Produce a technical child that explicitly selects no Discoveries."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def draft(self, prompt: str) -> TaskDecompositionDraft:
        self.prompts.append(prompt)
        parent_ref = re.search(r"Parent local reference: ([^\n]+)", prompt)
        assert parent_ref is not None
        return TaskDecompositionDraft.model_validate(
            {
                "parent_task_ref": parent_ref.group(1),
                "child_task_proposals": [
                    {
                        "title": "Prepare profiling inputs",
                        "description": "Identify inputs needed for the analysis.",
                        "scope": "input readiness only",
                        "parent_task_ref": parent_ref.group(1),
                        "motivated_by_discovery_refs": [],
                        "decomposition_rationale": "This is a prerequisite technical task.",
                        "readiness_status": "operational",
                        "readiness_reason": "It does not create an analytical hypothesis.",
                    }
                ],
            }
        )


class ReadyAnalyticalDecompositionModel:
    def draft(self, prompt: str) -> TaskDecompositionDraft:
        parent_match = re.search(r"Parent local reference: (task:[^\n]+)", prompt)
        profile_match = re.search(r"data_profile_ref \(use ([^\)]+)\)", prompt)
        assert parent_match is not None
        assert profile_match is not None
        return TaskDecompositionDraft(
            parent_task_ref=parent_match.group(1),
            child_task_proposals=[
                ChildTaskProposalDraft(
                    title="Ready child",
                    description="Execute one bounded test.",
                    scope="accepted profile",
                    parent_task_ref=parent_match.group(1),
                    motivated_by_discovery_refs=[],
                    decomposition_rationale="Terminal analytical follow-up.",
                    readiness_status="ready_analytical",
                    data_profile_ref=profile_match.group(1),
                    variables=["x", "y"],
                    evidence_expectation="A deterministic p-value.",
                    hypothesis_statement="x is associated with y.",
                    claim_type="association",
                    decision_rule=EvaluationThresholds(p_value=0.05),
                    validation_method="deterministic_test",
                    executor_id="deterministic",
                    method_parameters=[MethodParameter(name="alpha", value=0.05)],
                    deterministic_seed=11,
                )
            ],
        )


def _database_url(db_session) -> str:
    return str(db_session.get_bind().url)


def test_public_decomposition_drafts_child_specific_operations_and_waits_for_approval(
    db_session,
) -> None:
    discovery_id = uuid4()
    profile = DataProfileRecord(
        dataset_path="data/decomposition.csv",
        method=DataProfileMethod.BASELINE_SUMMARY,
        row_count=1,
        column_count=1,
        lifecycle_state=DataProfileLifecycleState.ACTIVE,
    )
    db_session.add(profile)
    db_session.add(ObjectiveRecord(title="Objective", statement="Bounded decomposition"))
    db_session.flush()
    source_task = TaskRecord(title="Source", description="Source", profile_id=profile.profile_id)
    db_session.add(source_task)
    db_session.flush()
    hypothesis = HypothesisRecord(
        task_id=source_task.task_id,
        profile_id=profile.profile_id,
        statement="Source hypothesis",
        scope="test scope",
        validation_method="test method",
        evidence_expectation="test evidence",
    )
    db_session.add(hypothesis)
    db_session.flush()
    ev_id = str(uuid4())
    db_session.add(
        DiscoveryRecord(
            discovery_id=discovery_id,
            claim={"statement": "Existing discovery", "scope": "test scope"},
            epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
            scope="test scope",
            hypothesis_id=hypothesis.hypothesis_id,
            evidence_ids=[ev_id],
            lifecycle_state=DiscoveryLifecycleState.ACTIVE,
            validity_basis={
                "data_profile_id": str(profile.profile_id),
                "analysis_frame_refs": ["test-frame"],
                "hypothesis_id": str(hypothesis.hypothesis_id),
                "evidence_ids": [ev_id],
                "method": "test method",
                "decision_rule": {},
                "assumptions_excluded_from_inference": True,
            },
        )
    )
    db_session.commit()
    parent = TaskRepository(db_session).create(
        Task(
            title="Parent analytical task",
            description="Decompose this parent.",
            profile_id=profile.profile_id,
            motivated_by_discovery_ids=[discovery_id],
        )
    )
    frame = SessionFrameRepository(db_session).create(
        SessionFrame(frame_topic="test", objective_snapshot="Keep the analysis bounded.")
    )
    model = EmptyMotivationDecompositionModel()
    graph = build_graph(checkpointer=MemorySaver())

    result = graph.invoke(
        {"query": f"/decompose {parent.task_id}"},
        config={"configurable": {"thread_id": "decomposition-test"}},
        context=Context(
            database_url=_database_url(db_session),
            session_id="decomposition-test",
            session_frame_id=frame.session_frame_id,
            task_decomposition_model=model,
        ),
    )

    operations = [
        PlannerOperation.model_validate(operation) for operation in result["planner_operations"]
    ]
    child_operation = next(
        operation
        for operation in operations
        if operation.operation_type == PlannerOperationType.CREATE_TASK
    )
    assert child_operation.payload["parent_task_id"] == str(parent.task_id)
    assert child_operation.payload["motivated_by_discovery_ids"] == []
    assert child_operation.payload["decomposition_rationale"] == (
        "This is a prerequisite technical task."
    )
    assert result["pending_interaction"].kind == "planner_operation_approval"
    assert TaskRepository(db_session).list(parent_task_id=parent.task_id) == []
    assert model.prompts and "Parent direct-motivation candidates:" in model.prompts[0]
    assert "Other bounded Discovery candidates:" in model.prompts[0]


def test_decomposition_commit_is_atomic_for_children_and_session_frame(db_session) -> None:
    db_session.add(ObjectiveRecord(title="Objective", statement="Bounded decomposition"))
    profile = DataProfileRecord(
        dataset_path="data/atomic-decomposition.csv",
        method=DataProfileMethod.BASELINE_SUMMARY,
        row_count=1,
        column_count=1,
        lifecycle_state=DataProfileLifecycleState.ACTIVE,
    )
    db_session.add(profile)
    db_session.commit()
    parent = TaskRepository(db_session).create(
        Task(title="Parent", description="Parent task", profile_id=profile.profile_id)
    )
    frame = SessionFrameRepository(db_session).create(
        SessionFrame(frame_topic="test", objective_snapshot="Bounded objective")
    )
    model = EmptyMotivationDecompositionModel()
    context = Context(
        database_url=_database_url(db_session),
        session_id="atomic-decomposition",
        session_frame_id=frame.session_frame_id,
        task_decomposition_model=model,
    )
    graph = build_graph(checkpointer=MemorySaver())
    result = graph.invoke(
        {"query": f"/decompose {parent.task_id}"},
        config={"configurable": {"thread_id": "atomic-decomposition"}},
        context=context,
    )
    operations = [
        PlannerOperation.model_validate(operation) for operation in result["planner_operations"]
    ]
    for operation in operations:
        operation.approval_state = PlannerOperationApprovalState.APPROVED
    operations[0].payload["parent_task_id"] = str(uuid4())

    outcome = commit_planner_operations(
        db_session,
        operations=operations,
        session_id="atomic-decomposition",
    )

    assert not outcome.succeeded
    assert TaskRepository(db_session).list(parent_task_id=parent.task_id) == []
    assert SessionFrameRepository(db_session).list_recent(limit=2) == [frame]


def test_decomposition_rejects_missing_active_data_profile(db_session) -> None:
    db_session.add(ObjectiveRecord(title="Objective", statement="Bounded decomposition"))
    db_session.commit()
    parent = TaskRepository(db_session).create(Task(title="Parent", description="Parent task"))
    frame = SessionFrameRepository(db_session).create(
        SessionFrame(frame_topic="test", objective_snapshot="Bounded objective")
    )

    result = build_graph(checkpointer=MemorySaver()).invoke(
        {"query": f"/decompose {parent.task_id}"},
        config={"configurable": {"thread_id": "missing-profile-decomposition"}},
        context=Context(
            database_url=_database_url(db_session),
            session_id="missing-profile-decomposition",
            session_frame_id=frame.session_frame_id,
        ),
    )

    assert result["controlled_error"].code == "decomposition_data_profile_missing"


def test_child_kind_contract_is_typed_and_not_forced_onto_non_analytical_children() -> None:
    parent_ref = "task:parent"
    profile_id = uuid4()
    ready = ReadyAnalyticalDecompositionModel().draft(
        "Parent local reference: task:parent\n"
        "data_profile_ref (use data_profile:active)"
    ).child_task_proposals[0]
    payload = ready.operation_payload(
        task_id=uuid4(),
        parent_task_id=uuid4(),
        motivated_by_discovery_ids=[],
        parent_task_updated_at=Task(title="P", description="P").updated_at,
        profile_id=profile_id,
        motivation_data_profile_id=profile_id,
    )
    assert payload.task_kind == TaskKind.ANALYTICAL
    assert payload.analytical_specification is not None
    assert payload.analytical_specification.data_profile_id == profile_id
    assert payload.analytical_specification.variable_bindings == ["x", "y"]

    for readiness_status in ("operational", "blocked", "requires_decomposition"):
        child = ChildTaskProposalDraft(
            title="Non-analytical child",
            description="No analytical contract.",
            scope="workflow",
            parent_task_ref=parent_ref,
            motivated_by_discovery_refs=[],
            decomposition_rationale="Workflow-only child.",
            readiness_status=readiness_status,
            readiness_reason="Not a terminal analytical leaf.",
        )
        non_analytical_payload = child.operation_payload(
            task_id=uuid4(),
            parent_task_id=uuid4(),
            motivated_by_discovery_ids=[],
            parent_task_updated_at=Task(title="P", description="P").updated_at,
        )
        assert non_analytical_payload.task_kind == TaskKind.ORGANIZING
        assert non_analytical_payload.analytical_specification is None

    with pytest.raises(ValueError, match="cannot carry an analytical execution contract"):
        ChildTaskProposalDraft(
            title="Technical child",
            description="Invalid analytical leakage.",
            scope="workflow",
            parent_task_ref=parent_ref,
            motivated_by_discovery_refs=[],
            decomposition_rationale="Invalid.",
            readiness_status="operational",
            readiness_reason="Technical.",
            variables=["x"],
        )
    with pytest.raises(ValueError, match="must not contain duplicates"):
        ChildTaskProposalDraft(
            title="Duplicate motivation",
            description="Invalid duplicate refs.",
            scope="workflow",
            parent_task_ref=parent_ref,
            motivated_by_discovery_refs=["discovery:a", "discovery:a"],
            decomposition_rationale="Invalid.",
            readiness_status="blocked",
            readiness_reason="Blocked.",
        )


def test_ready_child_commit_rejects_stale_profile_and_rolls_back_frame(db_session) -> None:
    db_session.add(ObjectiveRecord(title="Objective", statement="Stale profile guard"))
    db_session.commit()
    profiles = DataProfileRepository(db_session)
    old_profile = profiles.create(
        DataProfile(
            dataset_path="data/old.csv",
            method=DataProfileMethod.BASELINE_SUMMARY,
            schema_summary=SchemaSummary(column_order=["x", "y"]),
            baseline_summary=BaselineSummary(column_names=["x", "y"]),
            row_count=2,
            column_count=2,
            lifecycle_state=DataProfileLifecycleState.ACTIVE,
            accepted_as_ground_truth=True,
        )
    )
    replacement = profiles.create(
        old_profile.model_copy(
            update={
                "profile_id": uuid4(),
                "dataset_path": "data/replacement.csv",
            }
        )
    )
    parent = TaskRepository(db_session).create(
        Task(title="Parent", description="Parent", profile_id=old_profile.profile_id)
    )
    frame = SessionFrameRepository(db_session).create(
        SessionFrame(
            frame_topic="stale profile",
            objective_snapshot="Guard the active profile",
            active_data_profile_refs=[old_profile.profile_id],
        )
    )
    result = build_graph(checkpointer=MemorySaver()).invoke(
        {"query": f"/decompose {parent.task_id}"},
        config={"configurable": {"thread_id": "stale-profile-decomposition"}},
        context=Context(
            database_url=_database_url(db_session),
            session_id="stale-profile-decomposition",
            session_frame_id=frame.session_frame_id,
            task_decomposition_model=ReadyAnalyticalDecompositionModel(),
        ),
    )
    operations = [
        PlannerOperation.model_validate(operation) for operation in result["planner_operations"]
    ]
    assert len(operations) == 2
    profiles.supersede(old_profile.profile_id, replacement.profile_id)
    for operation in operations:
        operation.approval_state = PlannerOperationApprovalState.APPROVED

    outcome = commit_planner_operations(
        db_session,
        operations=operations,
        session_id="stale-profile-decomposition",
    )

    assert not outcome.succeeded
    assert TaskRepository(db_session).list(parent_task_id=parent.task_id) == []
    assert SessionFrameRepository(db_session).list_recent(limit=2) == [frame]
