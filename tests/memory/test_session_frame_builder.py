from __future__ import annotations

from uuid import uuid4

from memory import SessionFrameBuilder
from schemas.artifacts import DatasetAsset, Evidence, Hypothesis, Project
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
    DatasetKind,
    DatasetRole,
    DatasetSourceType,
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
