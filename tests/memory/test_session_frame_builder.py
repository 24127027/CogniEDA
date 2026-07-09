from __future__ import annotations

from uuid import uuid4

from memory import ContextBundle, ContextMode, SessionContextBuilder, SessionFrameBuilder
from schemas.artifacts import (
    Assumption,
    DataProfile,
    Discovery,
    Evidence,
    Hypothesis,
    Objective,
    Task,
)
from schemas.common import (
    BaselineSummary,
    DiscoveryClaim,
    DiscoveryContextSummary,
    EvidenceProvenance,
    EvidenceResultSummary,
    MethodParameter,
    SchemaSummary,
    ToolResultCacheSummary,
    ValidityBasis,
)
from schemas.enums import (
    AssumptionStatus,
    ConfidenceLevel,
    DataProfileLifecycleState,
    DataProfileMethod,
    DiscoveryEpistemicStatus,
    DiscoveryLifecycleState,
    EvidenceLifecycleState,
    EvidenceType,
    HypothesisStatus,
    MemoryStatus,
    ObjectiveStatus,
    SessionFrameStatus,
    TaskKind,
    TaskLifecycleState,
)


def build_objective() -> Objective:
    return Objective(
        title="Retention Investigation",
        statement="Explain retention differences.",
        status=ObjectiveStatus.ACTIVE,
    )


def build_profile() -> DataProfile:
    return DataProfile(
        dataset_path="data/retention.csv",
        dvc_hash="md5:retention-v1",
        dvc_version_label="retention-v1",
        method=DataProfileMethod.BASELINE_SUMMARY,
        schema_summary=SchemaSummary(column_order=["segment", "retained"]),
        baseline_summary=BaselineSummary(column_names=["segment", "retained"]),
        row_count=100,
        column_count=2,
        lifecycle_state=DataProfileLifecycleState.ACTIVE,
        accepted_as_ground_truth=True,
    )


def build_task(profile_id, **overrides: object) -> Task:
    payload: dict[str, object] = {
        "title": "Test segment retention",
        "description": "Evaluate whether segment and retention are associated.",
        "lifecycle_state": TaskLifecycleState.ACTIVE,
        "task_kind": TaskKind.ANALYTICAL,
        "profile_id": profile_id,
        "variables": ["segment", "retained"],
        "evidence_expectation": "Chi-square result.",
    }
    payload.update(overrides)
    return Task(**payload)


def build_hypothesis(task_id, profile_id, **overrides: object) -> Hypothesis:
    payload: dict[str, object] = {
        "task_id": task_id,
        "profile_id": profile_id,
        "statement": "Enterprise accounts retain longer than self-serve accounts.",
        "variables": ["segment", "retained"],
        "scope": "Accounts active in Q1",
        "validation_method": "chi_square",
        "evidence_expectation": "Chi-square test outcome.",
        "status": HypothesisStatus.TESTING,
    }
    payload.update(overrides)
    return Hypothesis(**payload)


def build_evidence(hypothesis_id, profile_id, **overrides: object) -> Evidence:
    payload: dict[str, object] = {
        "hypothesis_id": hypothesis_id,
        "profile_id": profile_id,
        "analysis_frame_ref": "analysis-frame:retention:v1:segment",
        "execution_run_ref": "execution-run:retention-001",
        "evidence_type": EvidenceType.STATISTICAL_TEST,
        "method": "chi_square",
        "provenance": EvidenceProvenance(
            analysis_frame_ref="analysis-frame:retention:v1:segment",
            execution_run_ref="execution-run:retention-001",
        ),
        "result_summary": EvidenceResultSummary(
            summary="Segment and retention are associated within the profiled scope.",
        ),
        "limitations": ["Domain semantics have not been validated yet."],
    }
    payload.update(overrides)
    return Evidence(**payload)


def build_discovery(
    hypothesis_id,
    profile_id,
    evidence_id,
    **overrides: object,
) -> Discovery:
    payload: dict[str, object] = {
        "hypothesis_id": hypothesis_id,
        "evidence_ids": [evidence_id],
        "claim": DiscoveryClaim(
            statement="Segment and retention are associated.",
            scope="Accounts active in Q1.",
        ),
        "epistemic_status": DiscoveryEpistemicStatus.SUPPORTED,
        "scope": "Accounts active in Q1.",
        "validity_basis": ValidityBasis(
            data_profile_id=profile_id,
            analysis_frame_refs=["analysis-frame:retention:v1:segment"],
            hypothesis_id=hypothesis_id,
            evidence_ids=[evidence_id],
            method="chi_square",
            parameters=[MethodParameter(name="alpha", value=0.05)],
            decision_rule="p_value < alpha",
            uncertainty="p_value=0.03",
        ),
    }
    payload.update(overrides)
    return Discovery(**payload)


def build_frame_with_discovery(
    lifecycle_state: DiscoveryLifecycleState,
) -> tuple[Discovery, object]:
    objective = build_objective()
    discovery = build_discovery(
        uuid4(),
        uuid4(),
        uuid4(),
        lifecycle_state=lifecycle_state,
    )
    frame = SessionFrameBuilder().build(
        objective=objective,
        discoveries=[discovery],
    )
    return discovery, frame


def get_discovery_exclusion_note(
    context: ContextBundle,
    discovery: Discovery,
) -> str:
    notes = [
        note
        for note in context.exclusion_notes
        if str(discovery.discovery_id) in note
    ]

    assert len(notes) == 1
    return notes[0]


def test_discovery_context_summary_carries_lifecycle_state() -> None:
    evidence_id = uuid4()
    summary = DiscoveryContextSummary(
        discovery_id=uuid4(),
        claim_statement="Segment and retention are associated.",
        epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
        scope="Accounts active in Q1.",
        evidence_ids=[evidence_id],
        lifecycle_state=DiscoveryLifecycleState.FLAGGED,
    )

    assert summary.lifecycle_state == DiscoveryLifecycleState.FLAGGED


def test_discovery_summary_copies_lifecycle_state_from_discovery() -> None:
    discovery = build_discovery(
        uuid4(),
        uuid4(),
        uuid4(),
        lifecycle_state=DiscoveryLifecycleState.INVALIDATED,
    )

    summary = SessionFrameBuilder._discovery_summary(discovery)

    assert summary.lifecycle_state == DiscoveryLifecycleState.INVALIDATED


def test_session_frame_builder_uses_profile_and_evidence_context() -> None:
    objective = build_objective()
    profile = build_profile()
    task = build_task(profile.profile_id)
    hypothesis = build_hypothesis(task.task_id, profile.profile_id)
    evidence = build_evidence(hypothesis.hypothesis_id, profile.profile_id)
    discovery = build_discovery(hypothesis.hypothesis_id, profile.profile_id, evidence.evidence_id)

    frame = SessionFrameBuilder().build(
        objective=objective,
        frame_topic="retention-frame",
        frame_status=SessionFrameStatus.CHECKPOINT,
        frame_outcome="Evidence supports the current retention hypothesis.",
        data_profiles=[profile],
        tasks=[task],
        hypotheses=[hypothesis],
        evidence=[evidence],
        discoveries=[discovery],
        cached_tool_results=[
            ToolResultCacheSummary(
                cache_key="retention_v1.profile",
                summary="Baseline profile for retention v1.",
                status=MemoryStatus.PINNED,
                created_at=evidence.created_at,
            )
        ],
    )

    assert frame.frame_topic == "retention-frame"
    assert frame.active_data_profile_refs == [profile.profile_id]
    assert frame.active_task_refs == [task.task_id]
    assert frame.active_hypotheses[0].linked_evidence_count == 1
    assert frame.supporting_evidence_refs == [evidence.evidence_id]
    assert frame.relevant_discovery_refs == [discovery.discovery_id]
    assert any(
        "Domain semantics have not been validated yet." in item for item in frame.key_warnings
    )


def test_session_context_builder_separates_planning_and_conclusion_context() -> None:
    objective = build_objective()
    profile = build_profile()
    task = build_task(profile.profile_id)
    assumption = Assumption(
        statement="Each row represents one account-month.",
        scope="Retention source data grain.",
        basis="Provided by the source-system owner.",
        confidence=ConfidenceLevel.MEDIUM,
        status=AssumptionStatus.ACTIVE,
        scoped_data_profile_ids=[profile.profile_id],
    )
    hypothesis = build_hypothesis(task.task_id, profile.profile_id)
    evidence = build_evidence(hypothesis.hypothesis_id, profile.profile_id)
    discovery = build_discovery(hypothesis.hypothesis_id, profile.profile_id, evidence.evidence_id)

    frame = SessionFrameBuilder().build(
        objective=objective,
        data_profiles=[profile],
        tasks=[task],
        assumptions=[assumption],
        hypotheses=[hypothesis],
        evidence=[evidence],
        discoveries=[discovery],
        pending_tasks=["Review account-month grain before deeper modeling."],
        open_questions=["Does retention exclude trial accounts?"],
    )

    context_builder = SessionContextBuilder()
    planning_context = context_builder.build(frame, mode=ContextMode.PLANNING)
    conclusion_context = context_builder.build(frame, mode=ContextMode.CONCLUSION)
    answer_context = context_builder.build(frame, mode=ContextMode.ANSWER)

    assert planning_context.assumption_refs == (assumption.assumption_id,)
    assert planning_context.task_refs == (task.task_id,)
    assert planning_context.pending_tasks == (
        "Review account-month grain before deeper modeling.",
    )

    assert conclusion_context.assumptions == ()
    assert conclusion_context.assumption_refs == ()
    assert conclusion_context.tasks == ()
    assert conclusion_context.task_refs == ()
    assert conclusion_context.user_decisions == ()
    assert conclusion_context.pending_tasks == ()
    assert conclusion_context.open_questions == ()
    assert conclusion_context.cached_tool_results == ()
    assert conclusion_context.data_profile_refs == (profile.profile_id,)
    assert conclusion_context.hypothesis_refs == (hypothesis.hypothesis_id,)
    assert conclusion_context.evidence_refs == (evidence.evidence_id,)
    assert conclusion_context.discovery_refs == ()
    assert answer_context.discovery_refs == (discovery.discovery_id,)
    assert "Assumptions are excluded" in conclusion_context.exclusion_notes[0]


def test_answer_context_excludes_flagged_discovery() -> None:
    discovery, frame = build_frame_with_discovery(DiscoveryLifecycleState.FLAGGED)

    answer_context = SessionContextBuilder().build(frame, mode=ContextMode.ANSWER)

    assert answer_context.discovery_refs == ()
    assert discovery.discovery_id not in answer_context.discovery_refs
    note = get_discovery_exclusion_note(answer_context, discovery)
    assert "answer context" in note
    assert "lifecycle_state=flagged" in note
    assert "Flagged Discovery requires review" in note


def test_answer_context_excludes_invalidated_discovery() -> None:
    discovery, frame = build_frame_with_discovery(DiscoveryLifecycleState.INVALIDATED)

    answer_context = SessionContextBuilder().build(frame, mode=ContextMode.ANSWER)

    assert answer_context.discovery_refs == ()
    assert discovery.discovery_id not in answer_context.discovery_refs
    note = get_discovery_exclusion_note(answer_context, discovery)
    assert "lifecycle_state=invalidated" in note
    assert "invalidated Discovery is not allowed" in note


def test_answer_context_excludes_deprecated_discovery() -> None:
    discovery, frame = build_frame_with_discovery(DiscoveryLifecycleState.DEPRECATED)

    answer_context = SessionContextBuilder().build(frame, mode=ContextMode.ANSWER)

    assert answer_context.discovery_refs == ()
    assert discovery.discovery_id not in answer_context.discovery_refs
    note = get_discovery_exclusion_note(answer_context, discovery)
    assert "lifecycle_state=deprecated" in note
    assert "deprecated Discovery is not allowed" in note


def test_answer_context_excludes_stale_memory_discovery_and_records_note() -> None:
    discovery, frame = build_frame_with_discovery(DiscoveryLifecycleState.ACTIVE)
    frame.relevant_discoveries[0].memory_status = MemoryStatus.STALE

    answer_context = SessionContextBuilder().build(frame, mode=ContextMode.ANSWER)

    assert answer_context.discovery_refs == ()
    assert discovery.discovery_id not in answer_context.discovery_refs
    note = get_discovery_exclusion_note(answer_context, discovery)
    assert "memory_status=stale" in note
    assert "lifecycle_state=active" in note
    assert "Discovery state 'stale' is not allowed" in note


def test_answer_context_includes_active_current_discovery() -> None:
    discovery, frame = build_frame_with_discovery(DiscoveryLifecycleState.ACTIVE)

    answer_context = SessionContextBuilder().build(frame, mode=ContextMode.ANSWER)

    assert answer_context.discovery_refs == (discovery.discovery_id,)


def test_planning_context_may_include_flagged_discovery_for_review() -> None:
    discovery, frame = build_frame_with_discovery(DiscoveryLifecycleState.FLAGGED)

    planning_context = SessionContextBuilder().build(frame, mode=ContextMode.PLANNING)

    assert planning_context.discovery_refs == (discovery.discovery_id,)
    assert not any(
        str(discovery.discovery_id) in note
        for note in planning_context.exclusion_notes
    )


def test_discovery_exclusion_notes_do_not_mutate_original_summary() -> None:
    _discovery, frame = build_frame_with_discovery(DiscoveryLifecycleState.INVALIDATED)
    original_summary = frame.relevant_discoveries[0]
    original_payload = original_summary.model_dump(mode="json")

    answer_context = SessionContextBuilder().build(frame, mode=ContextMode.ANSWER)

    assert answer_context.exclusion_notes
    assert original_summary.model_dump(mode="json") == original_payload
    assert not hasattr(original_summary, "exclusion_notes")


def test_conclusion_context_excludes_existing_discovery_regardless_of_lifecycle() -> None:
    context_builder = SessionContextBuilder()

    for lifecycle_state in DiscoveryLifecycleState:
        discovery, frame = build_frame_with_discovery(lifecycle_state)

        conclusion_context = context_builder.build(frame, mode=ContextMode.CONCLUSION)

        assert conclusion_context.discovery_refs == ()
        assert discovery.discovery_id not in conclusion_context.discovery_refs


def test_discovery_synthesis_context_excludes_existing_discovery_regardless_of_lifecycle() -> None:
    context_builder = SessionContextBuilder()

    for lifecycle_state in DiscoveryLifecycleState:
        discovery, frame = build_frame_with_discovery(lifecycle_state)

        synthesis_context = context_builder.build(
            frame,
            mode=ContextMode.DISCOVERY_SYNTHESIS,
        )

        assert synthesis_context.discovery_refs == ()
        assert discovery.discovery_id not in synthesis_context.discovery_refs


def test_conclusion_context_filters_stale_rejected_or_completed_items() -> None:
    objective = build_objective()
    profile = build_profile()
    task = build_task(profile.profile_id)
    hypothesis = build_hypothesis(
        task.task_id,
        profile.profile_id,
    )
    completed_hypothesis = build_hypothesis(
        task.task_id,
        profile.profile_id,
        status=HypothesisStatus.COMPLETED,
    )
    evidence = build_evidence(hypothesis.hypothesis_id, profile.profile_id)
    superseded_evidence = build_evidence(
        hypothesis.hypothesis_id,
        profile.profile_id,
        evidence_id=uuid4(),
        lifecycle_state=EvidenceLifecycleState.SUPERSEDED,
    )

    frame = SessionFrameBuilder().build(
        objective=objective,
        data_profiles=[profile],
        tasks=[task],
        hypotheses=[hypothesis, completed_hypothesis],
        evidence=[evidence, superseded_evidence],
    )
    frame.data_profile_summaries[0].memory_status = MemoryStatus.STALE
    frame.active_hypotheses[0].memory_status = MemoryStatus.REJECTED

    conclusion_context = SessionContextBuilder().build(frame, mode=ContextMode.CONCLUSION)

    assert conclusion_context.data_profile_summaries == ()
    assert conclusion_context.hypotheses == ()
    assert conclusion_context.evidence_refs == (evidence.evidence_id,)
    assert superseded_evidence.evidence_id not in conclusion_context.evidence_refs


def test_session_frame_keeps_proposed_tasks_for_planning_only() -> None:
    objective = build_objective()
    profile = build_profile()
    proposed_task = build_task(
        profile.profile_id,
        lifecycle_state=TaskLifecycleState.PROPOSED,
    )
    rejected_task = build_task(
        profile.profile_id,
        lifecycle_state=TaskLifecycleState.REJECTED,
    )

    frame = SessionFrameBuilder().build(
        objective=objective,
        data_profiles=[profile],
        tasks=[proposed_task, rejected_task],
    )

    context_builder = SessionContextBuilder()
    planning_context = context_builder.build(frame, mode=ContextMode.PLANNING)
    synthesis_context = context_builder.build(frame, mode=ContextMode.DISCOVERY_SYNTHESIS)

    assert frame.active_task_refs == [proposed_task.task_id]
    assert planning_context.task_refs == (proposed_task.task_id,)
    assert rejected_task.task_id not in planning_context.task_refs
    assert synthesis_context.task_refs == ()
