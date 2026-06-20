from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from repositories import (
    AssumptionRepository,
    AssumptionUpdate,
    DataProfileRepository,
    DatasetAssetRepository,
    DatasetAssetUpdate,
    DecisionLogRepository,
    DecisionLogUpdate,
    EvidenceRepository,
    HypothesisRepository,
    HypothesisUpdate,
    ProjectRepository,
    ProjectUpdate,
    SessionFrameRepository,
)
from schemas.artifacts import (
    Assumption,
    DataProfile,
    DatasetAsset,
    DecisionLog,
    Evidence,
    Hypothesis,
    Project,
    SessionFrame,
)
from schemas.common import (
    AssumptionContextSummary,
    BaselineSummary,
    ContextProvenance,
    DatasetContextSummary,
    DeadEndSummary,
    DecisionContextSummary,
    EvidenceContextSummary,
    EvidenceProvenance,
    EvidenceResultSummary,
    HypothesisContextSummary,
    HypothesisEvaluation,
    InvalidationRule,
    LineageStep,
    MethodParameter,
    QualityFlag,
    SchemaSummary,
    StaleContextMarker,
    ToolResultCacheSummary,
)
from schemas.enums import (
    AssumptionStatus,
    ConfidenceLevel,
    DataProfileMethod,
    DatasetKind,
    DatasetRole,
    DatasetSourceType,
    DecisionStatus,
    DecisionType,
    EvidenceType,
    HypothesisEvidenceOutcome,
    HypothesisStatus,
    InvalidationTrigger,
    LineageOperationType,
    MemorySourceType,
    MemoryStatus,
    ProjectStatus,
    QualityFlagSeverity,
    SessionFrameStatus,
)


def build_project(**overrides: object) -> Project:
    payload: dict[str, object] = {
        "name": "Churn Investigation",
        "objective": "Understand customer churn drivers.",
        "research_questions": ["What segments churn most?"],
        "status": ProjectStatus.ACTIVE,
    }
    payload.update(overrides)
    return Project(**payload)


def build_dataset_asset(project_id: UUID, **overrides: object) -> DatasetAsset:
    payload: dict[str, object] = {
        "project_id": project_id,
        "name": "customers",
        "source_type": DatasetSourceType.FILE,
        "location": "data/customers.csv",
        "version": "v1",
        "kind": DatasetKind.RAW,
        "role": DatasetRole.PRIMARY,
        "description": "Raw customer extract.",
    }
    payload.update(overrides)
    return DatasetAsset(**payload)


def build_data_profile(project_id: UUID, dataset_id: UUID, **overrides: object) -> DataProfile:
    payload: dict[str, object] = {
        "project_id": project_id,
        "dataset_id": dataset_id,
        "method": DataProfileMethod.BASELINE_SUMMARY,
        "schema_summary": SchemaSummary(column_order=["customer_id"]),
        "baseline_summary": BaselineSummary(column_names=["customer_id"]),
        "row_count": 10,
        "column_count": 1,
        "quality_flags": [
            QualityFlag(
                code="constant_column",
                severity=QualityFlagSeverity.INFO,
                message="Column has a single non-null value.",
                column_name="country",
            )
        ],
    }
    payload.update(overrides)
    return DataProfile(**payload)


def build_assumption(project_id: UUID, **overrides: object) -> Assumption:
    payload: dict[str, object] = {
        "project_id": project_id,
        "statement": "Each row represents one customer.",
        "basis": "Derived from unique customer identifier checks.",
        "confidence": ConfidenceLevel.MEDIUM,
        "status": AssumptionStatus.ACTIVE,
    }
    payload.update(overrides)
    return Assumption(**payload)


def build_hypothesis(project_id: UUID, **overrides: object) -> Hypothesis:
    payload: dict[str, object] = {
        "project_id": project_id,
        "statement": "Higher monthly spend is associated with lower churn.",
        "variables": ["monthly_spend", "churned"],
        "scope": "Active residential customers",
        "validation_method": "logistic_regression",
        "status": HypothesisStatus.PROPOSED,
        "assumption_ids": [],
        "dataset_ids": [],
    }
    payload.update(overrides)
    return Hypothesis(**payload)


def build_evidence(project_id: UUID, dataset_id: UUID, **overrides: object) -> Evidence:
    payload: dict[str, object] = {
        "project_id": project_id,
        "dataset_id": dataset_id,
        "evidence_type": EvidenceType.STATISTICAL_TEST,
        "method": "chi_square",
        "parameters": [MethodParameter(name="alpha", value=0.05)],
        "provenance": EvidenceProvenance(
            source_profile_id=uuid4(),
            execution_label="run-001",
            code_reference="tests/evidence",
            artifact_paths=["reports/evidence.json"],
        ),
        "result_summary": EvidenceResultSummary(
            summary="Association detected.",
            key_findings=["p-value below threshold"],
            metric_name="p_value",
            metric_value=0.01,
        ),
        "limitations": ["Small validation sample."],
        "assumption_ids": [],
        "hypothesis_evaluations": [],
        "decision_ids": [],
    }
    payload.update(overrides)
    return Evidence(**payload)


def build_decision_log(project_id: UUID, **overrides: object) -> DecisionLog:
    payload: dict[str, object] = {
        "project_id": project_id,
        "decision_type": DecisionType.VALIDATION_STRATEGY,
        "decision": "Use stratified validation split.",
        "rationale": "Protect minority churn cases.",
        "status": DecisionStatus.ACTIVE,
        "alternatives_considered": ["Random split"],
        "assumption_ids": [],
        "hypothesis_ids": [],
    }
    payload.update(overrides)
    return DecisionLog(**payload)


def build_session_frame(project_id: UUID, **overrides: object) -> SessionFrame:
    created_at = datetime.now(UTC)
    payload: dict[str, object] = {
        "project_id": project_id,
        "frame_topic": "missing-value-investigation-frame",
        "frame_status": SessionFrameStatus.HANDOFF,
        "objective_snapshot": "Understand customer churn drivers.",
        "frame_outcome": "Need a validation split decision before proceeding.",
        "project_summary": "Churn project summary.",
        "branch_key": "main",
        "checkpoint_label": "checkpoint-001",
        "handoff_summary": "Resume from the latest churn investigation checkpoint.",
        "dataset_summaries": [
            DatasetContextSummary(
                dataset_id=uuid4(),
                name="customers",
                version="v1",
                kind=DatasetKind.RAW,
                role=DatasetRole.PRIMARY,
                row_count=10,
                column_count=4,
                warning_count=1,
                provenance=[
                    ContextProvenance(
                        source_type=MemorySourceType.DATA_PROFILE,
                        reference="profile-001",
                    )
                ],
                invalidation_rules=[
                    InvalidationRule(
                        trigger=InvalidationTrigger.DATASET_VERSION_CHANGE,
                        detail="Refresh if the customers dataset version changes.",
                    )
                ],
            )
        ],
        "active_dataset_refs": [uuid4()],
        "active_assumptions": [
            AssumptionContextSummary(
                assumption_id=uuid4(),
                statement="Each row represents one customer.",
                confidence=ConfidenceLevel.MEDIUM,
                linked_evidence_count=1,
                memory_status=MemoryStatus.PINNED,
            )
        ],
        "active_assumption_refs": [uuid4()],
        "active_hypotheses": [
            HypothesisContextSummary(
                hypothesis_id=uuid4(),
                statement="Monthly spend reduces churn.",
                status=HypothesisStatus.PROPOSED,
                validation_method="logistic_regression",
                linked_evidence_count=1,
                invalidation_rules=[
                    InvalidationRule(
                        trigger=InvalidationTrigger.ASSUMPTION_REJECTED,
                        detail="Re-evaluate if the row-granularity assumption is rejected.",
                    )
                ],
            )
        ],
        "active_hypothesis_refs": [uuid4()],
        "strongest_evidence": [
            EvidenceContextSummary(
                evidence_id=uuid4(),
                evidence_type=EvidenceType.STATISTICAL_TEST,
                method="chi_square",
                summary="Association detected.",
                created_at=created_at,
                memory_status=MemoryStatus.VALIDATED,
                provenance=[
                    ContextProvenance(
                        source_type=MemorySourceType.VALIDATION_RESULT,
                        reference="run-001",
                    )
                ],
            )
        ],
        "strongest_evidence_refs": [uuid4()],
        "recent_decisions": [
            DecisionContextSummary(
                decision_id=uuid4(),
                decision_type=DecisionType.VALIDATION_STRATEGY,
                decision="Use stratified validation split.",
                status=DecisionStatus.ACTIVE,
                created_at=created_at,
                memory_status=MemoryStatus.PINNED,
            )
        ],
        "recent_decision_refs": [uuid4()],
        "pending_tasks": ["Validate churn hypotheses."],
        "open_questions": ["Do we need a time-based split?"],
        "key_warnings": ["Small validation sample."],
        "stale_context": [
            StaleContextMarker(
                artifact_type="Assumption",
                reason="Old uniqueness assumption was rejected on dataset_v0.",
            )
        ],
        "dead_ends": [
            DeadEndSummary(
                summary="Removed high spend outliers too early.",
                reason="The earlier filter erased genuine churn signal.",
                revived_only_if="Re-run with a documented leakage-safe outlier rule.",
            )
        ],
        "cached_tool_results": [
            ToolResultCacheSummary(
                cache_key="dataset_v1.profile",
                summary="Baseline profile for customers v1.",
                status=MemoryStatus.PINNED,
                source_type=MemorySourceType.TOOL_RESULT,
                created_at=created_at,
                expires_at=created_at + timedelta(days=1),
                invalidation_rules=[
                    InvalidationRule(
                        trigger=InvalidationTrigger.DATASET_VERSION_CHANGE,
                        detail="Drop the cache when customers moves off v1.",
                    )
                ],
            )
        ],
        "frame_invalidation_rules": [
            InvalidationRule(
                trigger=InvalidationTrigger.COMMIT_SHA_CHANGE,
                detail="Review code-linked context after a material code change.",
            )
        ],
        "created_at": created_at,
    }
    payload.update(overrides)
    return SessionFrame(**payload)


def test_project_repository_crud_and_active_filter(db_session) -> None:
    repository = ProjectRepository(db_session)

    active_project = repository.create(build_project())
    archived_project = repository.create(
        build_project(name="Archived", status=ProjectStatus.ARCHIVED)
    )

    updated = repository.update(
        active_project.project_id,
        ProjectUpdate(
            objective="Refined churn objective.",
            research_questions=["What segments churn most?", "What predicts churn?"],
        ),
    )

    assert updated is not None
    assert updated.objective == "Refined churn objective."
    assert repository.get_by_id(active_project.project_id) == updated
    assert [project.project_id for project in repository.list_active()] == [
        active_project.project_id
    ]
    assert [project.project_id for project in repository.list(status=ProjectStatus.ARCHIVED)] == [
        archived_project.project_id
    ]


def test_dataset_asset_repository_queries_and_update(db_session) -> None:
    project = ProjectRepository(db_session).create(build_project())
    repository = DatasetAssetRepository(db_session)

    parent = repository.create(build_dataset_asset(project.project_id, name="customers"))
    child = repository.create(
        build_dataset_asset(
            project.project_id,
            name="customers_clean",
            kind=DatasetKind.DERIVED,
            role=DatasetRole.INTERMEDIATE,
            upstream_dataset_ids=[parent.dataset_id],
            lineage_steps=[
                LineageStep(
                    operation_type=LineageOperationType.COLUMN_DROP,
                    description="Drop unused text column before modeling.",
                    input_dataset_ids=[parent.dataset_id],
                    column_names=["notes"],
                )
            ],
            version="v2",
        )
    )

    sibling = repository.create(
        build_dataset_asset(
            project.project_id,
            name="events",
            source_type=DatasetSourceType.QUERY,
            role=DatasetRole.REFERENCE,
        )
    )

    updated = repository.update(
        sibling.dataset_id,
        DatasetAssetUpdate(description=None, location="warehouse://events"),
    )

    assert updated is not None
    assert updated.description is None
    assert updated.location == "warehouse://events"
    assert child.upstream_dataset_ids == [parent.dataset_id]
    assert [item.dataset_id for item in repository.list_children(parent.dataset_id)] == [
        child.dataset_id
    ]
    assert [item.dataset_id for item in repository.list_upstream(child.dataset_id)] == [
        parent.dataset_id
    ]
    assert [
        item.dataset_id
        for item in repository.list_by_name(project.project_id, "customers")
    ] == [
        parent.dataset_id
    ]
    assert {
        item.dataset_id
        for item in repository.list(
            project_id=project.project_id,
            kind=DatasetKind.DERIVED,
        )
    } == {
        child.dataset_id
    }
    assert {item.dataset_id for item in repository.list(role=DatasetRole.REFERENCE)} == {
        sibling.dataset_id
    }


def test_dataset_asset_repository_enforces_unique_project_name_version(db_session) -> None:
    project = ProjectRepository(db_session).create(build_project())
    repository = DatasetAssetRepository(db_session)

    repository.create(build_dataset_asset(project.project_id, name="customers", version="v1"))

    with pytest.raises(IntegrityError):
        repository.create(build_dataset_asset(project.project_id, name="customers", version="v1"))


def test_data_profile_repository_queries_and_round_trip(db_session) -> None:
    project = ProjectRepository(db_session).create(build_project())
    dataset = DatasetAssetRepository(db_session).create(build_dataset_asset(project.project_id))
    repository = DataProfileRepository(db_session)

    older = repository.create(
        build_data_profile(
            project.project_id,
            dataset.dataset_id,
            created_at=datetime.now(UTC) - timedelta(days=1),
        )
    )
    newer = repository.create(
        build_data_profile(
            project.project_id,
            dataset.dataset_id,
            method=DataProfileMethod.DATA_QUALITY_SCAN,
        )
    )

    loaded = repository.get_by_id(older.profile_id)

    assert loaded is not None
    assert loaded.quality_flags[0].severity == QualityFlagSeverity.INFO
    assert repository.get_latest_for_dataset(dataset.dataset_id) == newer
    assert repository.get_latest_for_dataset(
        dataset.dataset_id,
        method=DataProfileMethod.BASELINE_SUMMARY,
    ) == older
    assert [item.profile_id for item in repository.list_for_dataset(dataset.dataset_id)] == [
        newer.profile_id,
        older.profile_id,
    ]


def test_assumption_repository_queries_and_update(db_session) -> None:
    project = ProjectRepository(db_session).create(build_project())
    dataset = DatasetAssetRepository(db_session).create(build_dataset_asset(project.project_id))
    profile = DataProfileRepository(db_session).create(
        build_data_profile(project.project_id, dataset.dataset_id)
    )
    repository = AssumptionRepository(db_session)

    active = repository.create(
        build_assumption(
            project.project_id,
            dataset_id=dataset.dataset_id,
            profile_id=profile.profile_id,
        )
    )
    repository.create(
        build_assumption(
            project.project_id,
            statement="Archived assumption",
            status=AssumptionStatus.ARCHIVED,
        )
    )

    updated = repository.update(
        active.assumption_id,
        AssumptionUpdate(
            status=AssumptionStatus.VALIDATED,
            profile_id=None,
        ),
    )

    assert updated is not None
    assert updated.status == AssumptionStatus.VALIDATED
    assert updated.profile_id is None
    assert repository.list_active(project_id=project.project_id) == []
    assert [item.assumption_id for item in repository.list_for_dataset(dataset.dataset_id)] == [
        active.assumption_id
    ]
    assert [item.assumption_id for item in repository.list(status=AssumptionStatus.ARCHIVED)] != []


def test_hypothesis_repository_queries_and_typed_update(db_session) -> None:
    project = ProjectRepository(db_session).create(build_project())
    dataset = DatasetAssetRepository(db_session).create(build_dataset_asset(project.project_id))
    assumption = AssumptionRepository(db_session).create(build_assumption(project.project_id))
    repository = HypothesisRepository(db_session)

    active = repository.create(
        build_hypothesis(
            project.project_id,
            dataset_ids=[dataset.dataset_id],
            assumption_ids=[assumption.assumption_id],
        )
    )
    repository.create(
        build_hypothesis(
            project.project_id,
            statement="Archived hypothesis",
            status=HypothesisStatus.ARCHIVED,
        )
    )

    updated = repository.update(
        active.hypothesis_id,
        HypothesisUpdate(
            status=HypothesisStatus.VALIDATING,
        ),
    )

    assert updated is not None
    assert updated.status == HypothesisStatus.VALIDATING
    assert [
        item.hypothesis_id
        for item in repository.list_active(project_id=project.project_id)
    ] == [
        active.hypothesis_id
    ]
    assert [item.hypothesis_id for item in repository.list_for_dataset(dataset.dataset_id)] == [
        active.hypothesis_id
    ]
    assert [
        item.hypothesis_id
        for item in repository.list_for_assumption(assumption.assumption_id)
    ] == [
        active.hypothesis_id
    ]


def test_evidence_repository_queries_and_nested_round_trip(db_session) -> None:
    project = ProjectRepository(db_session).create(build_project())
    dataset = DatasetAssetRepository(db_session).create(build_dataset_asset(project.project_id))
    assumption = AssumptionRepository(db_session).create(build_assumption(project.project_id))
    hypothesis = HypothesisRepository(db_session).create(build_hypothesis(project.project_id))
    decision = DecisionLogRepository(db_session).create(build_decision_log(project.project_id))
    repository = EvidenceRepository(db_session)

    evidence = repository.create(
        build_evidence(
            project.project_id,
            dataset.dataset_id,
            assumption_ids=[assumption.assumption_id],
            hypothesis_evaluations=[
                HypothesisEvaluation(
                    hypothesis_id=hypothesis.hypothesis_id,
                    outcome=HypothesisEvidenceOutcome.SUPPORTS,
                    note="Observed association aligns with the claim.",
                )
            ],
            decision_ids=[decision.decision_id],
        )
    )

    loaded = repository.get_by_id(evidence.evidence_id)

    assert loaded is not None
    assert loaded.parameters[0].name == "alpha"
    assert loaded.result_summary.metric_value == 0.01
    assert loaded.assumption_ids == [assumption.assumption_id]
    assert loaded.hypothesis_evaluations[0].outcome == HypothesisEvidenceOutcome.SUPPORTS
    assert [item.evidence_id for item in repository.list_for_dataset(dataset.dataset_id)] == [
        evidence.evidence_id
    ]
    assert [
        item.evidence_id
        for item in repository.list_for_assumption(assumption.assumption_id)
    ] == [
        evidence.evidence_id
    ]
    assert [
        item.evidence_id
        for item in repository.list_for_hypothesis(hypothesis.hypothesis_id)
    ] == [
        evidence.evidence_id
    ]
    assert [
        item.evidence_id
        for item in repository.list_for_hypothesis(
            hypothesis.hypothesis_id,
            outcome=HypothesisEvidenceOutcome.SUPPORTS,
        )
    ] == [
        evidence.evidence_id
    ]
    assert [item.evidence_id for item in repository.list_for_decision(decision.decision_id)] == [
        evidence.evidence_id
    ]


def test_decision_log_repository_filters_and_update(db_session) -> None:
    project = ProjectRepository(db_session).create(build_project())
    assumption = AssumptionRepository(db_session).create(build_assumption(project.project_id))
    hypothesis = HypothesisRepository(db_session).create(build_hypothesis(project.project_id))
    repository = DecisionLogRepository(db_session)

    older = repository.create(
        build_decision_log(
            project.project_id,
            decision="Older decision",
            created_at=datetime.now(UTC) - timedelta(days=1),
            updated_at=datetime.now(UTC) - timedelta(days=1),
        )
    )
    active = repository.create(
        build_decision_log(
            project.project_id,
            assumption_ids=[assumption.assumption_id],
            hypothesis_ids=[hypothesis.hypothesis_id],
        )
    )

    updated = repository.update(
        active.decision_id,
        DecisionLogUpdate(
            status=DecisionStatus.SUPERSEDED,
            superseded_by_decision_id=older.decision_id,
        ),
    )

    assert updated is not None
    assert updated.status == DecisionStatus.SUPERSEDED
    assert updated.superseded_by_decision_id == older.decision_id
    assert [item.decision_id for item in repository.list(status=DecisionStatus.SUPERSEDED)] == [
        active.decision_id
    ]
    assert [item.decision_id for item in repository.list_active(project_id=project.project_id)] == [
        older.decision_id
    ]
    assert [
        item.decision_id
        for item in repository.list_recent(project_id=project.project_id, limit=1)
    ] == [
        older.decision_id
    ]
    assert [
        item.decision_id
        for item in repository.list_recent(
            project_id=project.project_id,
            limit=1,
            active_only=False,
        )
    ] == [
        active.decision_id
    ]


def test_session_frame_repository_queries_and_nested_round_trip(db_session) -> None:
    project = ProjectRepository(db_session).create(build_project())
    repository = SessionFrameRepository(db_session)

    older = repository.create(
        build_session_frame(
            project.project_id,
            created_at=datetime.now(UTC) - timedelta(hours=1),
        )
    )
    latest = repository.create(
        build_session_frame(
            project.project_id,
            parent_session_frame_id=older.session_frame_id,
        )
    )

    loaded = repository.get_by_id(latest.session_frame_id)

    assert loaded is not None
    assert loaded.frame_topic == "missing-value-investigation-frame"
    assert loaded.frame_status == SessionFrameStatus.HANDOFF
    assert loaded.parent_session_frame_id == older.session_frame_id
    assert loaded.dataset_summaries[0].warning_count == 1
    assert loaded.dataset_summaries[0].provenance[0].source_type == MemorySourceType.DATA_PROFILE
    assert loaded.active_dataset_refs
    assert loaded.active_assumptions[0].memory_status == MemoryStatus.PINNED
    assert loaded.stale_context[0].artifact_type == "Assumption"
    assert loaded.cached_tool_results[0].cache_key == "dataset_v1.profile"
    assert repository.get_latest(project.project_id) == latest
    assert [
        item.session_frame_id
        for item in repository.list_recent(project.project_id, limit=1)
    ] == [
        latest.session_frame_id
    ]
    assert [item.session_frame_id for item in repository.list(project_id=project.project_id)] == [
        latest.session_frame_id,
        older.session_frame_id,
    ]


def test_append_only_and_immutable_repositories_do_not_expose_update(db_session) -> None:
    assert not hasattr(DataProfileRepository(db_session), "update")
    assert not hasattr(EvidenceRepository(db_session), "update")
    assert not hasattr(SessionFrameRepository(db_session), "update")
