import re
from uuid import uuid4

from langgraph.checkpoint.memory import MemorySaver

from agents.planner.graph import build_graph
from agents.planner.types import Context, TaskDecompositionDraft
from application.orchestrator.planner_commit import commit_planner_operations
from db.models import DataProfileRecord, DiscoveryRecord, HypothesisRecord, TaskRecord
from repositories import SessionFrameRepository, TaskRepository
from schemas.artifacts import SessionFrame, Task
from schemas.enums import (
    DataProfileMethod,
    DiscoveryEpistemicStatus,
    DiscoveryLifecycleState,
    PlannerOperationApprovalState,
    PlannerOperationType,
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
    )
    db_session.add(profile)
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
    db_session.add(
        DiscoveryRecord(
            discovery_id=discovery_id,
            claim={"statement": "Existing discovery", "scope": "test scope"},
            epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
            scope="test scope",
            hypothesis_id=hypothesis.hypothesis_id,
            evidence_ids=[],
            lifecycle_state=DiscoveryLifecycleState.ACTIVE,
            validity_basis={
                "data_profile_id": str(profile.profile_id),
                "analysis_frame_refs": ["test-frame"],
                "hypothesis_id": str(hypothesis.hypothesis_id),
                "evidence_ids": [],
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
    parent = TaskRepository(db_session).create(
        Task(title="Parent", description="Parent task")
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
