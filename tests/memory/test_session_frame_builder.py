from __future__ import annotations

from uuid import uuid4

from memory import ContextMode, SessionContextBuilder, SessionFrameBuilder
from schemas.artifacts import Assumption, DatasetAsset, DecisionLog, Evidence, Hypothesis, Project
from schemas.common import (
    DeadEndSummary,
    EvidenceProvenance,
    EvidenceResultSummary,
    HypothesisEvaluation,
    InvalidationRule,
    StaleContextMarker,
    ToolResultCacheSummary,
)
from schemas.enums import (
    AssumptionStatus,
    ConfidenceLevel,
    DatasetKind,
    DatasetRole,
    DatasetSourceType,
    DecisionStatus,
    DecisionType,
    EvidenceType,
    HypothesisEvidenceOutcome,
    HypothesisStatus,
    InvalidationTrigger,
    MemoryStatus,
    SessionFrameStatus,
)


def test_session_frame_builder_uses_evidence_links_and_evidence_only_dataset_context() -> None:
    project = Project(
        name="EDA Project",
        objective="Understand conversion behavior.",
    )
    dataset = DatasetAsset(
        project_id=project.project_id,
        name="events",
        source_type=DatasetSourceType.FILE,
        location="data/events.csv",
        version="v1",
        kind=DatasetKind.RAW,
        role=DatasetRole.PRIMARY,
    )
    hypothesis = Hypothesis(
        project_id=project.project_id,
        statement="Longer sessions increase conversion.",
        variables=["session_length", "converted"],
        scope="Web sessions in Q1",
        validation_method="logistic_regression",
        status=HypothesisStatus.PROPOSED,
        dataset_ids=[dataset.dataset_id],
    )
    evidence = Evidence(
        project_id=project.project_id,
        dataset_id=dataset.dataset_id,
        evidence_type=EvidenceType.STATISTICAL_TEST,
        method="logistic_regression",
        provenance=EvidenceProvenance(
            source_profile_id=uuid4(),
            execution_label="run-001",
        ),
        result_summary=EvidenceResultSummary(
            summary="Session length is positively associated with conversion.",
        ),
        hypothesis_evaluations=[
            HypothesisEvaluation(
                hypothesis_id=hypothesis.hypothesis_id,
                outcome=HypothesisEvidenceOutcome.SUPPORTS,
            )
        ],
    )

    frame = SessionFrameBuilder().build(
        project=project,
        frame_topic="conversion-investigation-frame",
        frame_status=SessionFrameStatus.CHECKPOINT,
        frame_outcome="Evidence supports the current conversion hypothesis.",
        datasets=[dataset],
        hypotheses=[hypothesis],
        evidence=[evidence],
        stale_context=[
            StaleContextMarker(
                artifact_type="Hypothesis",
                reason="Previous baseline hypothesis was superseded.",
            )
        ],
        dead_ends=[
            DeadEndSummary(
                summary="Grouped by user instead of session.",
                reason="The dataset grain is session-level, not user-level.",
            )
        ],
        cached_tool_results=[
            ToolResultCacheSummary(
                cache_key="events_v1.profile",
                summary="Baseline profile for events v1.",
                status=MemoryStatus.PINNED,
                created_at=evidence.created_at,
                invalidation_rules=[
                    InvalidationRule(
                        trigger=InvalidationTrigger.DATASET_VERSION_CHANGE,
                        detail="Drop the cache when the events dataset version changes.",
                    )
                ],
            )
        ],
    )

    assert frame.frame_topic == "conversion-investigation-frame"
    assert frame.frame_status == SessionFrameStatus.CHECKPOINT
    assert frame.frame_outcome == "Evidence supports the current conversion hypothesis."
    assert frame.active_dataset_refs == [dataset.dataset_id]
    assert frame.strongest_evidence_refs == [evidence.evidence_id]
    assert frame.active_hypotheses[0].linked_evidence_count == 1
    assert frame.strongest_evidence[0].memory_status == MemoryStatus.VALIDATED
    assert frame.cached_tool_results[0].cache_key == "events_v1.profile"
    assert frame.stale_context[0].artifact_type == "Hypothesis"


def test_session_frame_builder_keeps_dataset_visible_when_only_evidence_exists() -> None:
    project = Project(
        name="EDA Project",
        objective="Assess a newly ingested dataset.",
    )
    dataset = DatasetAsset(
        project_id=project.project_id,
        name="customers",
        source_type=DatasetSourceType.FILE,
        location="data/customers.csv",
        version="v1",
        kind=DatasetKind.RAW,
        role=DatasetRole.PRIMARY,
    )
    evidence = Evidence(
        project_id=project.project_id,
        dataset_id=dataset.dataset_id,
        evidence_type=EvidenceType.DATA_QUALITY_CHECK,
        method="baseline_profile_quality_scan",
        provenance=EvidenceProvenance(
            execution_label="profile-001",
        ),
        result_summary=EvidenceResultSummary(
            summary="Profile detected missing values that need review.",
        ),
        limitations=["Domain semantics have not been validated yet."],
    )

    frame = SessionFrameBuilder().build(
        project=project,
        datasets=[dataset],
        evidence=[evidence],
    )

    assert frame.frame_topic == project.name
    assert frame.active_dataset_refs == [dataset.dataset_id]
    assert frame.strongest_evidence_refs == [evidence.evidence_id]
    assert frame.dataset_summaries[0].invalidation_rules[0].trigger == (
        InvalidationTrigger.DATASET_VERSION_CHANGE
    )
    assert any(
        "Domain semantics have not been validated yet." in item
        for item in frame.key_warnings
    )


def test_session_context_builder_separates_planning_and_conclusion_context() -> None:
    project = Project(
        name="EDA Project",
        objective="Explain retention differences.",
    )
    dataset = DatasetAsset(
        project_id=project.project_id,
        name="retention",
        source_type=DatasetSourceType.FILE,
        location="data/retention.csv",
        version="v1",
        kind=DatasetKind.RAW,
        role=DatasetRole.PRIMARY,
    )
    assumption = Assumption(
        project_id=project.project_id,
        statement="Each row represents one account-month.",
        basis="Provided by the source-system owner.",
        confidence=ConfidenceLevel.MEDIUM,
        status=AssumptionStatus.ACTIVE,
        dataset_id=dataset.dataset_id,
    )
    hypothesis = Hypothesis(
        project_id=project.project_id,
        statement="Enterprise accounts retain longer than self-serve accounts.",
        variables=["segment", "retained"],
        scope="Accounts active in Q1",
        validation_method="chi_square",
        status=HypothesisStatus.VALIDATING,
        dataset_ids=[dataset.dataset_id],
        assumption_ids=[assumption.assumption_id],
    )
    evidence = Evidence(
        project_id=project.project_id,
        dataset_id=dataset.dataset_id,
        evidence_type=EvidenceType.STATISTICAL_TEST,
        method="chi_square",
        provenance=EvidenceProvenance(execution_label="retention-test-001"),
        result_summary=EvidenceResultSummary(
            summary="Segment and retention are associated within the profiled scope.",
        ),
        assumption_ids=[assumption.assumption_id],
        hypothesis_evaluations=[
            HypothesisEvaluation(
                hypothesis_id=hypothesis.hypothesis_id,
                outcome=HypothesisEvidenceOutcome.SUPPORTS,
            )
        ],
    )
    decision = DecisionLog(
        project_id=project.project_id,
        decision_type=DecisionType.VALIDATION_STRATEGY,
        decision="Use chi-square before modeling.",
        rationale="Both fields are categorical in the current profile.",
        status=DecisionStatus.ACTIVE,
        hypothesis_ids=[hypothesis.hypothesis_id],
    )

    frame = SessionFrameBuilder().build(
        project=project,
        datasets=[dataset],
        assumptions=[assumption],
        hypotheses=[hypothesis],
        evidence=[evidence],
        decisions=[decision],
        pending_tasks=["Review account-month grain before deeper modeling."],
        open_questions=["Does retention exclude trial accounts?"],
        cached_tool_results=[
            ToolResultCacheSummary(
                cache_key="retention_v1.profile",
                summary="Baseline profile for retention v1.",
                status=MemoryStatus.PINNED,
                created_at=evidence.created_at,
            )
        ],
        stale_context=[
            StaleContextMarker(
                artifact_type="Assumption",
                reason="A previous grain assumption was superseded.",
            )
        ],
        dead_ends=[
            DeadEndSummary(
                summary="Tried revenue buckets before segment.",
                reason="Buckets were not stable across months.",
            )
        ],
    )

    context_builder = SessionContextBuilder()
    planning_context = context_builder.build(frame, mode=ContextMode.PLANNING)
    conclusion_context = context_builder.build(frame, mode=ContextMode.CONCLUSION)

    assert planning_context.assumption_refs == (assumption.assumption_id,)
    assert planning_context.pending_tasks == (
        "Review account-month grain before deeper modeling.",
    )
    assert planning_context.cached_tool_results[0].cache_key == "retention_v1.profile"
    assert planning_context.decisions[0].decision_id == decision.decision_id

    assert conclusion_context.assumptions == ()
    assert conclusion_context.assumption_refs == ()
    assert conclusion_context.decisions == ()
    assert conclusion_context.pending_tasks == ()
    assert conclusion_context.open_questions == ()
    assert conclusion_context.cached_tool_results == ()
    assert conclusion_context.stale_context == ()
    assert conclusion_context.dead_ends == ()
    assert conclusion_context.hypothesis_refs == (hypothesis.hypothesis_id,)
    assert conclusion_context.evidence_refs == (evidence.evidence_id,)
    assert "Assumptions are excluded" in conclusion_context.exclusion_notes[0]


def test_conclusion_context_filters_stale_or_rejected_memory_items() -> None:
    project = Project(
        name="EDA Project",
        objective="Review stale context filtering.",
    )
    dataset = DatasetAsset(
        project_id=project.project_id,
        name="events",
        source_type=DatasetSourceType.FILE,
        location="data/events.csv",
        version="v1",
        kind=DatasetKind.RAW,
        role=DatasetRole.PRIMARY,
    )
    hypothesis = Hypothesis(
        project_id=project.project_id,
        statement="Event count predicts conversion.",
        variables=["event_count", "converted"],
        scope="Current events profile",
        validation_method="logistic_regression",
        status=HypothesisStatus.VALIDATING,
        dataset_ids=[dataset.dataset_id],
    )
    evidence = Evidence(
        project_id=project.project_id,
        dataset_id=dataset.dataset_id,
        evidence_type=EvidenceType.STATISTICAL_TEST,
        method="logistic_regression",
        provenance=EvidenceProvenance(execution_label="old-run-001"),
        result_summary=EvidenceResultSummary(summary="Older result."),
        hypothesis_evaluations=[
            HypothesisEvaluation(
                hypothesis_id=hypothesis.hypothesis_id,
                outcome=HypothesisEvidenceOutcome.SUPPORTS,
            )
        ],
    )

    frame = SessionFrameBuilder().build(
        project=project,
        datasets=[dataset],
        hypotheses=[hypothesis],
        evidence=[evidence],
    )
    frame.dataset_summaries[0].memory_status = MemoryStatus.STALE
    frame.active_hypotheses[0].memory_status = MemoryStatus.REJECTED
    frame.strongest_evidence[0].memory_status = MemoryStatus.SUPERSEDED

    conclusion_context = SessionContextBuilder().build(frame, mode=ContextMode.CONCLUSION)

    assert conclusion_context.dataset_summaries == ()
    assert conclusion_context.hypotheses == ()
    assert conclusion_context.evidence == ()
    assert conclusion_context.active_dataset_refs == ()
    assert conclusion_context.hypothesis_refs == ()
    assert conclusion_context.evidence_refs == ()
