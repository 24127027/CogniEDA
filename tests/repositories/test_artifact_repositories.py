from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from db.init_db import init_db
from db.models import ExecutionRunRecord
from db.session import create_db_engine, get_session
from repositories import (
    AnalysisFrameRepository,
    AssumptionRepository,
    AssumptionUpdate,
    DataProfileRepository,
    DiscoveryRepository,
    EvidenceRepository,
    HypothesisRepository,
    HypothesisUpdate,
    ObjectiveRepository,
    ObjectiveRevisionRepository,
    ObjectiveUpdate,
    SessionFrameRepository,
    TaskRepository,
    TaskUpdate,
    UserDecisionRepository,
)
from schemas.artifacts import (
    Assumption,
    DataProfile,
    Discovery,
    EvaluationThresholds,
    Evidence,
    Hypothesis,
    Objective,
    SessionFrame,
    Task,
    UserDecision,
)
from schemas.common import (
    BaselineSummary,
    DiscoveryClaim,
    EvidenceProvenance,
    EvidenceResultSummary,
    MethodParameter,
    QualityFlag,
    SchemaSummary,
    ValidityBasis,
)
from schemas.enums import (
    AssumptionSource,
    AssumptionStatus,
    AssumptionTestability,
    ConfidenceLevel,
    DataProfileLifecycleState,
    DataProfileMethod,
    DiscoveryEpistemicStatus,
    DiscoveryLifecycleState,
    EvidenceLifecycleState,
    EvidenceType,
    ExecutionRunStatus,
    FirstClassObjectType,
    HypothesisStatus,
    ObjectiveStatus,
    QualityFlagSeverity,
    SessionFrameStatus,
    TaskKind,
    TaskLifecycleState,
    UserDecisionType,
)
from schemas.provenance import AnalysisFrame, ObjectiveRevision


def build_objective(**overrides: object) -> Objective:
    payload: dict[str, object] = {
        "title": "Churn Investigation",
        "statement": "Understand customer churn drivers.",
        "status": ObjectiveStatus.ACTIVE,
    }
    payload.update(overrides)
    return Objective(**payload)


def build_data_profile(**overrides: object) -> DataProfile:
    payload: dict[str, object] = {
        "dataset_path": "data/customers.csv",
        "dvc_hash": "md5:customers-v1",
        "dvc_version_label": "customers-v1",
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
        "lifecycle_state": DataProfileLifecycleState.ACTIVE,
        "accepted_as_ground_truth": True,
    }
    payload.update(overrides)
    return DataProfile(**payload)


def build_assumption(
    *,
    profile_id: UUID | None = None,
    **overrides: object,
) -> Assumption:
    payload: dict[str, object] = {
        "statement": "Each row represents one customer.",
        "scope": "Customer-level churn analysis.",
        "source": AssumptionSource.USER,
        "testability": AssumptionTestability.UNTESTABLE_IN_PROJECT,
        "basis": "Derived from unique customer identifier checks.",
        "confidence": ConfidenceLevel.MEDIUM,
        "status": AssumptionStatus.ACTIVE,
        "scoped_data_profile_ids": [profile_id] if profile_id is not None else [],
    }
    payload.update(overrides)
    return Assumption(**payload)


def build_task(profile_id: UUID | None, **overrides: object) -> Task:
    payload: dict[str, object] = {
        "title": "Test churn association",
        "description": "Evaluate whether monthly spend relates to churn.",
        "lifecycle_state": TaskLifecycleState.ACTIVE,
        "task_kind": TaskKind.ANALYTICAL,
        "profile_id": profile_id,
        "variables": ["monthly_spend", "churned"],
        "evidence_expectation": "A statistical test over the accepted DataProfile.",
    }
    payload.update(overrides)
    return Task(**payload)


def build_hypothesis(task_id: UUID, profile_id: UUID, **overrides: object) -> Hypothesis:
    payload: dict[str, object] = {
        "task_id": task_id,
        "profile_id": profile_id,
        "statement": "Higher monthly spend is associated with lower churn.",
        "variables": ["monthly_spend", "churned"],
        "scope": "Active residential customers",
        "validation_method": "logistic_regression",
        "evidence_expectation": "Regression coefficient and uncertainty.",
        "status": HypothesisStatus.TESTING,
    }
    payload.update(overrides)
    return Hypothesis(**payload)


def build_evidence(hypothesis_id: UUID, profile_id: UUID, **overrides: object) -> Evidence:
    payload: dict[str, object] = {
        "hypothesis_id": hypothesis_id,
        "profile_id": profile_id,
        "analysis_frame_ref": "analysis-frame:customers:v1:spend-churn",
        "execution_run_ref": "execution-run:001",
        "evidence_type": EvidenceType.STATISTICAL_TEST,
        "method": "logistic_regression",
        "parameters": [MethodParameter(name="alpha", value=0.05)],
        "provenance": EvidenceProvenance(
            analysis_frame_ref="analysis-frame:customers:v1:spend-churn",
            execution_run_ref="execution-run:001",
            code_reference="tests/evidence",
            artifact_paths=["reports/evidence.json"],
        ),
        "result_summary": EvidenceResultSummary(
            summary="Available evidence supports a negative association within scope.",
            key_findings=["coefficient below zero"],
            metric_name="p_value",
            metric_value=0.01,
        ),
        "limitations": ["Small validation sample."],
    }
    payload.update(overrides)
    return Evidence(**payload)


def build_discovery(
    hypothesis_id: UUID,
    profile_id: UUID,
    evidence_id: UUID,
    **overrides: object,
) -> Discovery:
    payload: dict[str, object] = {
        "hypothesis_id": hypothesis_id,
        "evidence_ids": [evidence_id],
        "claim": DiscoveryClaim(
            statement="Higher monthly spend is associated with lower churn.",
            scope="Active residential customers in the profiled dataset.",
            conditions=["logistic_regression", "alpha=0.05"],
            result="supported",
        ),
        "epistemic_status": DiscoveryEpistemicStatus.SUPPORTED,
        "scope": "Active residential customers in the profiled dataset.",
        "validity_basis": ValidityBasis(
            data_profile_id=profile_id,
            analysis_frame_refs=["analysis-frame:customers:v1:spend-churn"],
            hypothesis_id=hypothesis_id,
            evidence_ids=[evidence_id],
            method="logistic_regression",
            parameters=[MethodParameter(name="alpha", value=0.05)],
            code_reference="tests/evidence",
            environment_reference="pytest",
            decision_rule=EvaluationThresholds(p_value=0.05),
            strength="moderate",
            uncertainty="p_value=0.01",
            invalidators=["DataProfile superseded", "method implementation changes"],
        ),
    }
    payload.update(overrides)
    return Discovery(**payload)


def evidence_without_lifecycle_metadata(evidence: Evidence) -> dict[str, object]:
    return evidence.model_dump(
        exclude={"lifecycle_state", "superseded_by_evidence_id", "lifecycle_reason"}
    )


def discovery_without_review_metadata(discovery: Discovery) -> dict[str, object]:
    return discovery.model_dump(
        exclude={"lifecycle_state", "review_reasons", "flagged_by_evidence_ids"}
    )


def create_evidence_bound_discovery(
    db_session,
    *,
    evidence_overrides: dict[str, object] | None = None,
    discovery_overrides: dict[str, object] | None = None,
) -> tuple[DataProfile, Hypothesis, Evidence, Discovery]:
    profile = DataProfileRepository(db_session).create(build_data_profile())
    hypothesis, evidence, discovery = create_evidence_bound_discovery_for_profile(
        db_session,
        profile=profile,
        evidence_overrides=evidence_overrides,
        discovery_overrides=discovery_overrides,
    )
    return profile, hypothesis, evidence, discovery


def create_evidence_bound_discovery_for_profile(
    db_session,
    *,
    profile: DataProfile,
    evidence_overrides: dict[str, object] | None = None,
    discovery_overrides: dict[str, object] | None = None,
) -> tuple[Hypothesis, Evidence, Discovery]:
    task = TaskRepository(db_session).create(build_task(profile.profile_id))
    hypothesis = HypothesisRepository(db_session).create(
        build_hypothesis(task.task_id, profile.profile_id)
    )
    evidence = EvidenceRepository(db_session).create(
        build_evidence(
            hypothesis.hypothesis_id,
            profile.profile_id,
            **(evidence_overrides or {}),
        )
    )
    discovery = DiscoveryRepository(db_session).create(
        build_discovery(
            hypothesis.hypothesis_id,
            profile.profile_id,
            evidence.evidence_id,
            **(discovery_overrides or {}),
        )
    )
    return hypothesis, evidence, discovery


def test_obsolete_domain_types_are_not_exported_or_fcos() -> None:
    fcos = {item.value for item in FirstClassObjectType}

    assert fcos == {
        "objective",
        "data_profile",
        "assumption",
        "task",
        "hypothesis",
        "evidence",
        "discovery",
        "session_frame",
    }
    assert "project" not in fcos
    assert "workspace" not in fcos
    assert "dataset_asset" not in fcos
    assert "decision_log" not in fcos

    import schemas.artifacts as artifacts

    assert not hasattr(artifacts, "Project")
    assert not hasattr(artifacts, "DatasetAsset")
    assert not hasattr(artifacts, "DecisionLog")


def test_objective_task_profile_repositories_round_trip_without_project_ids(db_session) -> None:
    objective_repository = ObjectiveRepository(db_session)
    profile_repository = DataProfileRepository(db_session)
    task_repository = TaskRepository(db_session)

    objective = objective_repository.create(build_objective())
    updated_objective = objective_repository.update(
        objective.objective_id,
        ObjectiveUpdate(statement="Refined churn objective."),
    )
    profile = profile_repository.create(build_data_profile())
    task = task_repository.create(build_task(profile.profile_id))

    updated_task = task_repository.update(
        task.task_id,
        TaskUpdate(lifecycle_state=TaskLifecycleState.PAUSED),
    )

    assert updated_objective is not None
    assert updated_objective.statement == "Refined churn objective."
    assert profile_repository.get_latest_for_dataset_path("data/customers.csv") == profile
    assert profile_repository.list(dvc_hash="md5:customers-v1") == [profile]
    assert updated_task is not None
    assert updated_task.lifecycle_state == TaskLifecycleState.PAUSED
    assert "project_id" not in DataProfile.model_fields
    assert "workspace_id" not in DataProfile.model_fields


def test_objective_revision_is_non_fco_provenance() -> None:
    fcos = {item.value for item in FirstClassObjectType}

    assert "objective_revision" not in fcos

    import schemas.artifacts as artifacts
    import schemas.provenance as provenance

    assert not hasattr(artifacts, "ObjectiveRevision")
    assert hasattr(provenance, "ObjectiveRevision")


def test_objective_revision_repository_create_get_list_for_objective(db_session) -> None:
    objective_repository = ObjectiveRepository(db_session)
    revision_repository = ObjectiveRevisionRepository(db_session)
    objective = objective_repository.create(build_objective())
    other_objective = objective_repository.create(build_objective(title="Retention Investigation"))

    revision = revision_repository.create(
        ObjectiveRevision(
            objective_id=objective.objective_id,
            previous_title="Churn Investigation",
            previous_description="Understand customer churn drivers.",
            previous_lifecycle_state=ObjectiveStatus.ACTIVE,
            new_title="Churn Investigation",
            new_description="Understand churn drivers by segment.",
            new_lifecycle_state=ObjectiveStatus.ACTIVE,
            changed_fields=["statement"],
            revision_reason="Scope was narrowed.",
            planner_operation_id="planner-operation-1",
            user_decision_id="decision-1",
            created_by="test",
        )
    )
    other_revision = revision_repository.create(
        ObjectiveRevision(
            objective_id=other_objective.objective_id,
            previous_title="Retention Investigation",
            previous_description="Understand customer churn drivers.",
            previous_lifecycle_state=ObjectiveStatus.ACTIVE,
            new_title="Retention Investigation",
            new_description="Understand retention drivers.",
            new_lifecycle_state=ObjectiveStatus.ACTIVE,
            changed_fields=["statement"],
        )
    )

    loaded = revision_repository.get(revision.objective_revision_id)

    assert loaded == revision
    assert revision_repository.list_for_objective(objective.objective_id) == [revision]
    assert revision_repository.list_for_objective(other_objective.objective_id) == [other_revision]


def test_objective_update_with_revision_repository_creates_revision(
    db_session,
) -> None:
    objective_repository = ObjectiveRepository(db_session)
    revision_repository = ObjectiveRevisionRepository(db_session)
    objective = objective_repository.create(build_objective())

    updated = objective_repository.update(
        objective.objective_id,
        ObjectiveUpdate(
            title="Segmented Churn Investigation",
            statement="Understand churn drivers by segment.",
        ),
        revision_repository=revision_repository,
        revision_reason="Narrowed objective scope.",
        planner_operation_id="planner-operation-1",
        user_decision_id="decision-1",
        created_by="test",
    )

    revisions = revision_repository.list_for_objective(objective.objective_id)

    assert updated is not None
    assert updated.objective_id == objective.objective_id
    assert updated.title == "Segmented Churn Investigation"
    assert updated.statement == "Understand churn drivers by segment."
    assert len(objective_repository.list()) == 1
    assert len(revisions) == 1
    revision = revisions[0]
    assert revision.objective_id == objective.objective_id
    assert revision.previous_title == "Churn Investigation"
    assert revision.previous_description == "Understand customer churn drivers."
    assert revision.previous_lifecycle_state == ObjectiveStatus.ACTIVE
    assert revision.new_title == "Segmented Churn Investigation"
    assert revision.new_description == "Understand churn drivers by segment."
    assert revision.new_lifecycle_state == ObjectiveStatus.ACTIVE
    assert revision.changed_fields == ["title", "statement"]
    assert revision.revision_reason == "Narrowed objective scope."
    assert revision.planner_operation_id == "planner-operation-1"
    assert revision.user_decision_id == "decision-1"
    assert revision.created_by == "test"


def test_objective_update_rejects_revision_repository_from_different_session(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'objective_sessions.sqlite3').as_posix()}"
    create_db_engine.cache_clear()
    init_db(database_url)
    objective_session = get_session(database_url)
    revision_session = get_session(database_url)
    try:
        objective_repository = ObjectiveRepository(objective_session)
        revision_repository = ObjectiveRevisionRepository(revision_session)
        objective = objective_repository.create(build_objective())

        with pytest.raises(
            ValueError,
            match=(
                "Objective update and ObjectiveRevision creation must share "
                "the same SQLModel session"
            ),
        ):
            objective_repository.update(
                objective.objective_id,
                ObjectiveUpdate(statement="This update must be rejected."),
                revision_repository=revision_repository,
            )

        reloaded = objective_repository.get_by_id(objective.objective_id)

        assert reloaded is not None
        assert reloaded.title == objective.title
        assert reloaded.statement == objective.statement
        assert reloaded.status == objective.status
        assert (
            ObjectiveRevisionRepository(objective_session).list_for_objective(
                objective.objective_id
            )
            == []
        )
        assert revision_repository.list_for_objective(objective.objective_id) == []
    finally:
        objective_session.close()
        revision_session.close()
        create_db_engine.cache_clear()


def test_objective_update_without_revision_repository_preserves_behavior(
    db_session,
) -> None:
    objective_repository = ObjectiveRepository(db_session)
    objective = objective_repository.create(build_objective())

    updated = objective_repository.update(
        objective.objective_id,
        ObjectiveUpdate(statement="Refined churn objective."),
    )

    assert updated is not None
    assert updated.objective_id == objective.objective_id
    assert updated.statement == "Refined churn objective."
    assert ObjectiveRevisionRepository(db_session).list_for_objective(objective.objective_id) == []


def test_objective_noop_update_with_revision_repository_does_not_create_revision(
    db_session,
) -> None:
    objective_repository = ObjectiveRepository(db_session)
    revision_repository = ObjectiveRevisionRepository(db_session)
    objective = objective_repository.create(build_objective())

    updated = objective_repository.update(
        objective.objective_id,
        ObjectiveUpdate(statement=objective.statement),
        revision_repository=revision_repository,
        revision_reason="No semantic change.",
    )

    assert updated is not None
    assert updated.objective_id == objective.objective_id
    assert revision_repository.list_for_objective(objective.objective_id) == []


def test_data_profile_supersede_marks_old_profile_and_records_replacement(
    db_session,
) -> None:
    repository = DataProfileRepository(db_session)
    old_profile = repository.create(build_data_profile())
    replacement_profile = repository.create(
        build_data_profile(
            dataset_path="data/customers-cleaned.csv",
            dvc_hash="md5:customers-v2",
            dvc_version_label="customers-v2",
        )
    )

    superseded = repository.supersede(
        old_profile.profile_id,
        replacement_profile.profile_id,
        reason="Cleaning produced a replacement DataProfile.",
    )
    unchanged_replacement = repository.get_by_id(replacement_profile.profile_id)

    assert superseded is not None
    assert superseded.lifecycle_state == DataProfileLifecycleState.SUPERSEDED
    assert superseded.superseded_by_data_profile_id == replacement_profile.profile_id
    assert unchanged_replacement is not None
    assert unchanged_replacement.lifecycle_state == DataProfileLifecycleState.ACTIVE
    assert unchanged_replacement.superseded_by_data_profile_id is None


def test_data_profile_supersede_with_repositories_marks_historical_scope(
    db_session,
) -> None:
    profile_repository = DataProfileRepository(db_session)
    old_profile = profile_repository.create(build_data_profile())
    replacement_profile = profile_repository.create(
        build_data_profile(
            dataset_path="data/customers-cleaned.csv",
            dvc_hash="md5:customers-v2",
            dvc_version_label="customers-v2",
        )
    )
    unrelated_profile = profile_repository.create(
        build_data_profile(
            dataset_path="data/orders.csv",
            dvc_hash="md5:orders-v1",
            dvc_version_label="orders-v1",
        )
    )
    _, evidence, discovery = create_evidence_bound_discovery_for_profile(
        db_session,
        profile=old_profile,
    )
    _, unrelated_evidence, unrelated_discovery = create_evidence_bound_discovery_for_profile(
        db_session,
        profile=unrelated_profile,
    )
    evidence_repository = EvidenceRepository(db_session)
    discovery_repository = DiscoveryRepository(db_session)
    original_evidence_payload = evidence_without_lifecycle_metadata(evidence)
    original_discovery_payload = discovery_without_review_metadata(discovery)

    superseded_profile = profile_repository.supersede(
        old_profile.profile_id,
        replacement_profile.profile_id,
        reason="Cleaning produced a replacement DataProfile.",
        evidence_repository=evidence_repository,
        discovery_repository=discovery_repository,
    )

    historically_scoped = evidence_repository.get_by_id(evidence.evidence_id)
    flagged = discovery_repository.get_by_id(discovery.discovery_id)
    unaffected_evidence = evidence_repository.get_by_id(unrelated_evidence.evidence_id)
    unaffected_discovery = discovery_repository.get_by_id(unrelated_discovery.discovery_id)

    assert superseded_profile is not None
    assert superseded_profile.lifecycle_state == DataProfileLifecycleState.SUPERSEDED
    assert superseded_profile.superseded_by_data_profile_id == replacement_profile.profile_id
    assert historically_scoped is not None
    assert historically_scoped.lifecycle_state == EvidenceLifecycleState.HISTORICALLY_SCOPED
    assert historically_scoped.lifecycle_reason is not None
    assert str(old_profile.profile_id) in historically_scoped.lifecycle_reason
    assert str(replacement_profile.profile_id) in historically_scoped.lifecycle_reason
    assert "Cleaning produced a replacement DataProfile." in (historically_scoped.lifecycle_reason)
    assert historically_scoped.result_summary == evidence.result_summary
    assert evidence_without_lifecycle_metadata(historically_scoped) == (original_evidence_payload)

    assert flagged is not None
    assert flagged.lifecycle_state == DiscoveryLifecycleState.FLAGGED
    assert len(flagged.review_reasons) == 1
    assert str(old_profile.profile_id) in flagged.review_reasons[0]
    assert str(replacement_profile.profile_id) in flagged.review_reasons[0]
    assert "Cleaning produced a replacement DataProfile." in flagged.review_reasons[0]
    assert flagged.claim == discovery.claim
    assert flagged.validity_basis == discovery.validity_basis
    assert discovery_without_review_metadata(flagged) == original_discovery_payload

    assert unaffected_evidence is not None
    assert unaffected_evidence.lifecycle_state == EvidenceLifecycleState.ACTIVE
    assert unaffected_evidence.lifecycle_reason is None
    assert unaffected_evidence.result_summary == unrelated_evidence.result_summary
    assert unaffected_discovery is not None
    assert unaffected_discovery.lifecycle_state == DiscoveryLifecycleState.ACTIVE
    assert unaffected_discovery.review_reasons == []


def test_data_profile_supersede_with_only_evidence_repository_marks_historical_scope(
    db_session,
) -> None:
    profile_repository = DataProfileRepository(db_session)
    old_profile = profile_repository.create(build_data_profile())
    replacement_profile = profile_repository.create(
        build_data_profile(
            dataset_path="data/customers-cleaned.csv",
            dvc_hash="md5:customers-v2",
            dvc_version_label="customers-v2",
        )
    )
    _, evidence, discovery = create_evidence_bound_discovery_for_profile(
        db_session,
        profile=old_profile,
    )
    evidence_repository = EvidenceRepository(db_session)
    discovery_repository = DiscoveryRepository(db_session)

    profile_repository.supersede(
        old_profile.profile_id,
        replacement_profile.profile_id,
        evidence_repository=evidence_repository,
    )

    superseded_profile = profile_repository.get_by_id(old_profile.profile_id)
    historically_scoped = evidence_repository.get_by_id(evidence.evidence_id)
    unchanged_discovery = discovery_repository.get_by_id(discovery.discovery_id)

    assert superseded_profile is not None
    assert superseded_profile.lifecycle_state == DataProfileLifecycleState.SUPERSEDED
    assert superseded_profile.superseded_by_data_profile_id == replacement_profile.profile_id
    assert historically_scoped is not None
    assert historically_scoped.lifecycle_state == EvidenceLifecycleState.HISTORICALLY_SCOPED
    assert unchanged_discovery is not None
    assert unchanged_discovery.lifecycle_state == DiscoveryLifecycleState.ACTIVE
    assert unchanged_discovery.review_reasons == []


def test_data_profile_supersede_with_only_discovery_repository_flags_review(
    db_session,
) -> None:
    profile_repository = DataProfileRepository(db_session)
    old_profile = profile_repository.create(build_data_profile())
    replacement_profile = profile_repository.create(
        build_data_profile(
            dataset_path="data/customers-cleaned.csv",
            dvc_hash="md5:customers-v2",
            dvc_version_label="customers-v2",
        )
    )
    _, evidence, discovery = create_evidence_bound_discovery_for_profile(
        db_session,
        profile=old_profile,
    )
    evidence_repository = EvidenceRepository(db_session)
    discovery_repository = DiscoveryRepository(db_session)

    profile_repository.supersede(
        old_profile.profile_id,
        replacement_profile.profile_id,
        discovery_repository=discovery_repository,
    )

    superseded_profile = profile_repository.get_by_id(old_profile.profile_id)
    unchanged_evidence = evidence_repository.get_by_id(evidence.evidence_id)
    flagged_discovery = discovery_repository.get_by_id(discovery.discovery_id)

    assert superseded_profile is not None
    assert superseded_profile.lifecycle_state == DataProfileLifecycleState.SUPERSEDED
    assert superseded_profile.superseded_by_data_profile_id == replacement_profile.profile_id
    assert unchanged_evidence is not None
    assert unchanged_evidence.lifecycle_state == EvidenceLifecycleState.ACTIVE
    assert unchanged_evidence.lifecycle_reason is None
    assert flagged_discovery is not None
    assert flagged_discovery.lifecycle_state == DiscoveryLifecycleState.FLAGGED
    assert len(flagged_discovery.review_reasons) == 1


def test_data_profile_supersede_rejects_evidence_repository_from_different_session(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'data_profile_evidence_sessions.sqlite3').as_posix()}"
    create_db_engine.cache_clear()
    init_db(database_url)
    profile_session = get_session(database_url)
    evidence_session = get_session(database_url)
    verification_session = get_session(database_url)
    try:
        profile_repository = DataProfileRepository(profile_session)
        old_profile = profile_repository.create(build_data_profile())
        replacement_profile = profile_repository.create(
            build_data_profile(
                dataset_path="data/customers-cleaned.csv",
                dvc_hash="md5:customers-v2",
                dvc_version_label="customers-v2",
            )
        )
        _, evidence, discovery = create_evidence_bound_discovery_for_profile(
            profile_session,
            profile=old_profile,
        )

        with pytest.raises(
            ValueError,
            match=(
                "DataProfile supersession and dependent Evidence/Discovery propagation "
                "must share the same SQLModel session"
            ),
        ):
            profile_repository.supersede(
                old_profile.profile_id,
                replacement_profile.profile_id,
                evidence_repository=EvidenceRepository(evidence_session),
                discovery_repository=DiscoveryRepository(profile_session),
            )

        persisted_profile = DataProfileRepository(verification_session).get_by_id(
            old_profile.profile_id
        )
        persisted_evidence = EvidenceRepository(verification_session).get_by_id(
            evidence.evidence_id
        )
        persisted_discovery = DiscoveryRepository(verification_session).get_by_id(
            discovery.discovery_id
        )

        assert persisted_profile is not None
        assert persisted_evidence is not None
        assert persisted_discovery is not None
        assert persisted_profile.lifecycle_state == DataProfileLifecycleState.ACTIVE
        assert persisted_profile.superseded_by_data_profile_id is None
        assert persisted_evidence.lifecycle_state == EvidenceLifecycleState.ACTIVE
        assert persisted_evidence.lifecycle_reason is None
        assert persisted_discovery.lifecycle_state == DiscoveryLifecycleState.ACTIVE
        assert persisted_discovery.review_reasons == []
        assert persisted_discovery.flagged_by_evidence_ids == []
    finally:
        profile_session.close()
        evidence_session.close()
        verification_session.close()
        create_db_engine.cache_clear()


def test_data_profile_supersede_rejects_discovery_repository_from_different_session(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'data_profile_discovery_sessions.sqlite3').as_posix()}"
    create_db_engine.cache_clear()
    init_db(database_url)
    profile_session = get_session(database_url)
    discovery_session = get_session(database_url)
    verification_session = get_session(database_url)
    try:
        profile_repository = DataProfileRepository(profile_session)
        old_profile = profile_repository.create(build_data_profile())
        replacement_profile = profile_repository.create(
            build_data_profile(
                dataset_path="data/customers-cleaned.csv",
                dvc_hash="md5:customers-v2",
                dvc_version_label="customers-v2",
            )
        )
        _, evidence, discovery = create_evidence_bound_discovery_for_profile(
            profile_session,
            profile=old_profile,
        )

        with pytest.raises(
            ValueError,
            match=(
                "DataProfile supersession and dependent Evidence/Discovery propagation "
                "must share the same SQLModel session"
            ),
        ):
            profile_repository.supersede(
                old_profile.profile_id,
                replacement_profile.profile_id,
                evidence_repository=EvidenceRepository(profile_session),
                discovery_repository=DiscoveryRepository(discovery_session),
            )

        persisted_profile = DataProfileRepository(verification_session).get_by_id(
            old_profile.profile_id
        )
        persisted_evidence = EvidenceRepository(verification_session).get_by_id(
            evidence.evidence_id
        )
        persisted_discovery = DiscoveryRepository(verification_session).get_by_id(
            discovery.discovery_id
        )

        assert persisted_profile is not None
        assert persisted_evidence is not None
        assert persisted_discovery is not None
        assert persisted_profile.lifecycle_state == DataProfileLifecycleState.ACTIVE
        assert persisted_profile.superseded_by_data_profile_id is None
        assert persisted_evidence.lifecycle_state == EvidenceLifecycleState.ACTIVE
        assert persisted_evidence.lifecycle_reason is None
        assert persisted_discovery.lifecycle_state == DiscoveryLifecycleState.ACTIVE
        assert persisted_discovery.review_reasons == []
        assert persisted_discovery.flagged_by_evidence_ids == []
    finally:
        profile_session.close()
        discovery_session.close()
        verification_session.close()
        create_db_engine.cache_clear()


def test_repeated_data_profile_supersession_is_rejected(db_session) -> None:
    repository = DataProfileRepository(db_session)
    old_profile = repository.create(build_data_profile())
    replacement_profile = repository.create(
        build_data_profile(
            dataset_path="data/customers-cleaned.csv",
            dvc_hash="md5:customers-v2",
            dvc_version_label="customers-v2",
        )
    )

    repository.supersede(old_profile.profile_id, replacement_profile.profile_id)

    with pytest.raises(ValueError, match="already superseded"):
        repository.supersede(old_profile.profile_id, replacement_profile.profile_id)


def test_assumption_repository_is_planning_scoped_by_profile(db_session) -> None:
    profile = DataProfileRepository(db_session).create(build_data_profile())
    repository = AssumptionRepository(db_session)

    active = repository.create(build_assumption(profile_id=profile.profile_id))
    repository.create(build_assumption(statement="Archived", status=AssumptionStatus.ARCHIVED))
    task = TaskRepository(db_session).create(build_task(profile.profile_id))
    hypothesis = HypothesisRepository(db_session).create(
        build_hypothesis(task.task_id, profile.profile_id)
    )
    evidence = EvidenceRepository(db_session).create(
        build_evidence(hypothesis.hypothesis_id, profile.profile_id)
    )
    discovery = DiscoveryRepository(db_session).create(
        build_discovery(hypothesis.hypothesis_id, profile.profile_id, evidence.evidence_id)
    )
    flagged = repository.flag_for_contradiction(
        active.assumption_id,
        discovery_id=discovery.discovery_id,
    )
    updated = repository.update(
        active.assumption_id,
        AssumptionUpdate(status=AssumptionStatus.RETAINED),
    )

    assert flagged is not None
    assert flagged.status == AssumptionStatus.FLAGGED
    assert flagged.statement == active.statement
    assert flagged.contradicted_by_discovery_ids == [discovery.discovery_id]
    assert updated is not None
    assert updated.status == AssumptionStatus.RETAINED
    assert repository.list_active() == []
    assert repository.list_for_profile(profile.profile_id) == [updated]


def test_assumption_admission_and_update_do_not_rewrite_truth() -> None:
    with pytest.raises(ValidationError):
        build_assumption(
            testability=AssumptionTestability.TESTABLE_CLAIM_REJECTED_AS_ASSUMPTION,
        )

    with pytest.raises(ValidationError):
        AssumptionUpdate(statement="Rewrite the assumption statement.")


def test_hypothesis_evidence_discovery_are_traceable_and_evidence_bound(db_session) -> None:
    profile = DataProfileRepository(db_session).create(build_data_profile())
    task = TaskRepository(db_session).create(build_task(profile.profile_id))
    hypothesis_repository = HypothesisRepository(db_session)
    evidence_repository = EvidenceRepository(db_session)
    discovery_repository = DiscoveryRepository(db_session)

    hypothesis = hypothesis_repository.create(build_hypothesis(task.task_id, profile.profile_id))
    evidence = evidence_repository.create(
        build_evidence(hypothesis.hypothesis_id, profile.profile_id)
    )
    discovery = discovery_repository.create(
        build_discovery(hypothesis.hypothesis_id, profile.profile_id, evidence.evidence_id)
    )
    with pytest.raises(ValueError):
        discovery_repository.create(
            build_discovery(hypothesis.hypothesis_id, profile.profile_id, evidence.evidence_id)
        )
    updated_hypothesis = hypothesis_repository.update(
        hypothesis.hypothesis_id,
        HypothesisUpdate(status=HypothesisStatus.CONFIRMED),
    )

    assert evidence.profile_id == profile.profile_id
    assert evidence.analysis_frame_ref == "analysis-frame:customers:v1:spend-churn"
    assert evidence.execution_run_ref == "execution-run:001"
    assert discovery.evidence_ids == [evidence.evidence_id]
    assert discovery.validity_basis.data_profile_id == profile.profile_id
    assert discovery.validity_basis.assumptions_excluded_from_inference is True
    assert discovery_repository.list_for_hypothesis(hypothesis.hypothesis_id) == [discovery]
    assert updated_hypothesis is not None
    assert updated_hypothesis.status == HypothesisStatus.CONFIRMED


def test_analysis_frame_and_execution_run_are_minimal_provenance_refs(db_session) -> None:
    profile = DataProfileRepository(db_session).create(build_data_profile())
    task = TaskRepository(db_session).create(build_task(profile.profile_id))
    hypothesis = HypothesisRepository(db_session).create(
        build_hypothesis(task.task_id, profile.profile_id)
    )
    analysis_frame = AnalysisFrameRepository(db_session).create(
        AnalysisFrame(
            data_profile_id=profile.profile_id,
            frame_hash="frame-hash:customers:v1",
            column_refs=["monthly_spend", "churned"],
            row_filter_description="Active residential customers only.",
        )
    )
    execution_run = ExecutionRunRecord(
        execution_run_id=uuid4(),
        task_id=task.task_id,
        hypothesis_id=hypothesis.hypothesis_id,
        analysis_frame_id=analysis_frame.analysis_frame_id,
        executor_type="hypothesis_analyst",
        method_id="logistic_regression",
        parameter_hash="params:alpha-005",
        status=ExecutionRunStatus.COMPLETED,
        dispatch_idempotency_key="key",
        attempt_version=1,
    )
    db_session.add(execution_run)
    db_session.commit()
    evidence = EvidenceRepository(db_session).create(
        build_evidence(
            hypothesis.hypothesis_id,
            profile.profile_id,
            analysis_frame_ref=str(analysis_frame.analysis_frame_id),
            execution_run_ref=str(execution_run.execution_run_id),
            provenance=EvidenceProvenance(
                analysis_frame_ref=str(analysis_frame.analysis_frame_id),
                execution_run_ref=str(execution_run.execution_run_id),
                code_reference="tests/evidence",
            ),
        )
    )

    assert "analysis_frame" not in {item.value for item in FirstClassObjectType}
    assert "execution_run" not in {item.value for item in FirstClassObjectType}
    assert AnalysisFrameRepository(db_session).list(data_profile_id=profile.profile_id) == [
        analysis_frame
    ]
    from sqlmodel import select
    runs = db_session.exec(select(ExecutionRunRecord).where(ExecutionRunRecord.hypothesis_id == hypothesis.hypothesis_id)).all()
    assert len(runs) == 1
    assert runs[0].execution_run_id == execution_run.execution_run_id
    assert evidence.analysis_frame_ref == str(analysis_frame.analysis_frame_id)
    assert evidence.execution_run_ref == str(execution_run.execution_run_id)


def test_evidence_creation_succeeds_with_strict_provenance_validation(db_session) -> None:
    profile = DataProfileRepository(db_session).create(build_data_profile())
    task = TaskRepository(db_session).create(build_task(profile.profile_id))
    hypothesis = HypothesisRepository(db_session).create(
        build_hypothesis(task.task_id, profile.profile_id)
    )
    analysis_frame = AnalysisFrameRepository(db_session).create(
        AnalysisFrame(
            data_profile_id=profile.profile_id,
            frame_hash="frame-hash:customers:v1",
        )
    )
    execution_run = ExecutionRunRecord(
        execution_run_id=uuid4(),
        task_id=task.task_id,
        hypothesis_id=hypothesis.hypothesis_id,
        analysis_frame_id=analysis_frame.analysis_frame_id,
        status=ExecutionRunStatus.COMPLETED,
        dispatch_idempotency_key="key",
        attempt_version=1,
    )
    db_session.add(execution_run)
    db_session.commit()

    evidence = EvidenceRepository(
        db_session,
        strict_provenance_validation=True,
    ).create(
        build_evidence(
            hypothesis.hypothesis_id,
            profile.profile_id,
            analysis_frame_ref=str(analysis_frame.analysis_frame_id),
            execution_run_ref=str(execution_run.execution_run_id),
            provenance=EvidenceProvenance(
                analysis_frame_ref=str(analysis_frame.analysis_frame_id),
                execution_run_ref=str(execution_run.execution_run_id),
                code_reference="tests/evidence",
            ),
        )
    )

    assert evidence.analysis_frame_ref == str(analysis_frame.analysis_frame_id)
    assert evidence.execution_run_ref == str(execution_run.execution_run_id)


def test_evidence_creation_fails_for_missing_analysis_frame_in_strict_mode(
    db_session,
) -> None:
    profile = DataProfileRepository(db_session).create(build_data_profile())
    task = TaskRepository(db_session).create(build_task(profile.profile_id))
    hypothesis = HypothesisRepository(db_session).create(
        build_hypothesis(task.task_id, profile.profile_id)
    )
    execution_run = ExecutionRunRecord(
        execution_run_id=uuid4(),
        task_id=task.task_id,
        hypothesis_id=hypothesis.hypothesis_id,
        status=ExecutionRunStatus.COMPLETED,
        dispatch_idempotency_key="key",
        attempt_version=1,
    )
    db_session.add(execution_run)
    db_session.commit()
    missing_analysis_frame_ref = str(uuid4())

    with pytest.raises(ValueError, match="existing AnalysisFrame"):
        EvidenceRepository(db_session, strict_provenance_validation=True).create(
            build_evidence(
                hypothesis.hypothesis_id,
                profile.profile_id,
                analysis_frame_ref=missing_analysis_frame_ref,
                execution_run_ref=str(execution_run.execution_run_id),
                provenance=EvidenceProvenance(
                    analysis_frame_ref=missing_analysis_frame_ref,
                    execution_run_ref=str(execution_run.execution_run_id),
                ),
            )
        )


def test_evidence_creation_fails_for_missing_execution_run_in_strict_mode(
    db_session,
) -> None:
    profile = DataProfileRepository(db_session).create(build_data_profile())
    task = TaskRepository(db_session).create(build_task(profile.profile_id))
    hypothesis = HypothesisRepository(db_session).create(
        build_hypothesis(task.task_id, profile.profile_id)
    )
    analysis_frame = AnalysisFrameRepository(db_session).create(
        AnalysisFrame(
            data_profile_id=profile.profile_id,
            frame_hash="frame-hash:customers:v1",
        )
    )
    missing_execution_run_ref = str(uuid4())

    with pytest.raises(ValueError, match="existing ExecutionRun"):
        EvidenceRepository(db_session, strict_provenance_validation=True).create(
            build_evidence(
                hypothesis.hypothesis_id,
                profile.profile_id,
                analysis_frame_ref=str(analysis_frame.analysis_frame_id),
                execution_run_ref=missing_execution_run_ref,
                provenance=EvidenceProvenance(
                    analysis_frame_ref=str(analysis_frame.analysis_frame_id),
                    execution_run_ref=missing_execution_run_ref,
                ),
            )
        )


def test_evidence_creation_fails_for_analysis_frame_profile_mismatch(
    db_session,
) -> None:
    profile = DataProfileRepository(db_session).create(build_data_profile())
    other_profile = DataProfileRepository(db_session).create(
        build_data_profile(
            dataset_path="data/customers-v2.csv",
            dvc_hash="md5:customers-v2",
            dvc_version_label="customers-v2",
        )
    )
    task = TaskRepository(db_session).create(build_task(profile.profile_id))
    hypothesis = HypothesisRepository(db_session).create(
        build_hypothesis(task.task_id, profile.profile_id)
    )
    analysis_frame = AnalysisFrameRepository(db_session).create(
        AnalysisFrame(
            data_profile_id=other_profile.profile_id,
            frame_hash="frame-hash:customers:v2",
        )
    )
    execution_run = ExecutionRunRecord(
        execution_run_id=uuid4(),
        task_id=task.task_id,
        hypothesis_id=hypothesis.hypothesis_id,
        status=ExecutionRunStatus.COMPLETED,
        dispatch_idempotency_key="key",
        attempt_version=1,
    )
    db_session.add(execution_run)
    db_session.commit()

    with pytest.raises(ValueError, match="data_profile_id must match"):
        EvidenceRepository(db_session, strict_provenance_validation=True).create(
            build_evidence(
                hypothesis.hypothesis_id,
                profile.profile_id,
                analysis_frame_ref=str(analysis_frame.analysis_frame_id),
                execution_run_ref=str(execution_run.execution_run_id),
                provenance=EvidenceProvenance(
                    analysis_frame_ref=str(analysis_frame.analysis_frame_id),
                    execution_run_ref=str(execution_run.execution_run_id),
                ),
            )
        )


def test_evidence_creation_fails_for_execution_run_hypothesis_mismatch(
    db_session,
) -> None:
    profile = DataProfileRepository(db_session).create(build_data_profile())
    first_task = TaskRepository(db_session).create(build_task(profile.profile_id))
    second_task = TaskRepository(db_session).create(build_task(profile.profile_id))
    first_hypothesis = HypothesisRepository(db_session).create(
        build_hypothesis(first_task.task_id, profile.profile_id)
    )
    second_hypothesis = HypothesisRepository(db_session).create(
        build_hypothesis(second_task.task_id, profile.profile_id)
    )
    analysis_frame = AnalysisFrameRepository(db_session).create(
        AnalysisFrame(
            data_profile_id=profile.profile_id,
            frame_hash="frame-hash:customers:v1",
        )
    )
    execution_run = ExecutionRunRecord(
        execution_run_id=uuid4(),
        task_id=second_task.task_id,
        hypothesis_id=second_hypothesis.hypothesis_id,
        analysis_frame_id=analysis_frame.analysis_frame_id,
        status=ExecutionRunStatus.COMPLETED,
        dispatch_idempotency_key="key",
        attempt_version=1,
    )
    db_session.add(execution_run)
    db_session.commit()

    with pytest.raises(ValueError, match="hypothesis_id must match"):
        EvidenceRepository(db_session, strict_provenance_validation=True).create(
            build_evidence(
                first_hypothesis.hypothesis_id,
                profile.profile_id,
                analysis_frame_ref=str(analysis_frame.analysis_frame_id),
                execution_run_ref=str(execution_run.execution_run_id),
                provenance=EvidenceProvenance(
                    analysis_frame_ref=str(analysis_frame.analysis_frame_id),
                    execution_run_ref=str(execution_run.execution_run_id),
                ),
            )
        )


def test_evidence_creation_keeps_non_strict_skeleton_refs(db_session) -> None:
    profile = DataProfileRepository(db_session).create(build_data_profile())
    task = TaskRepository(db_session).create(build_task(profile.profile_id))
    hypothesis = HypothesisRepository(db_session).create(
        build_hypothesis(task.task_id, profile.profile_id)
    )

    evidence = EvidenceRepository(db_session).create(
        build_evidence(hypothesis.hypothesis_id, profile.profile_id)
    )

    assert evidence.analysis_frame_ref == "analysis-frame:customers:v1:spend-churn"
    assert evidence.execution_run_ref == "execution-run:001"


def test_evidence_supersede_only_changes_lifecycle_metadata(db_session) -> None:
    profile = DataProfileRepository(db_session).create(build_data_profile())
    task = TaskRepository(db_session).create(build_task(profile.profile_id))
    hypothesis = HypothesisRepository(db_session).create(
        build_hypothesis(task.task_id, profile.profile_id)
    )
    evidence_repository = EvidenceRepository(db_session)
    evidence = evidence_repository.create(
        build_evidence(hypothesis.hypothesis_id, profile.profile_id)
    )
    replacement = evidence_repository.create(
        build_evidence(
            hypothesis.hypothesis_id,
            profile.profile_id,
            execution_run_ref="execution-run:replacement",
            provenance=EvidenceProvenance(
                analysis_frame_ref="analysis-frame:customers:v1:spend-churn",
                execution_run_ref="execution-run:replacement",
                code_reference="tests/evidence",
            ),
        )
    )

    superseded = evidence_repository.supersede(
        evidence.evidence_id,
        replacement.evidence_id,
        reason="Corrected executor output supersedes this Evidence.",
    )

    assert superseded is not None
    assert superseded.lifecycle_state == EvidenceLifecycleState.SUPERSEDED
    assert superseded.superseded_by_evidence_id == replacement.evidence_id
    assert superseded.lifecycle_reason == "Corrected executor output supersedes this Evidence."
    assert superseded.result_summary == evidence.result_summary
    assert evidence_without_lifecycle_metadata(superseded) == (
        evidence_without_lifecycle_metadata(evidence)
    )


def test_evidence_invalidate_only_changes_lifecycle_metadata(db_session) -> None:
    profile = DataProfileRepository(db_session).create(build_data_profile())
    task = TaskRepository(db_session).create(build_task(profile.profile_id))
    hypothesis = HypothesisRepository(db_session).create(
        build_hypothesis(task.task_id, profile.profile_id)
    )
    evidence_repository = EvidenceRepository(db_session)
    evidence = evidence_repository.create(
        build_evidence(hypothesis.hypothesis_id, profile.profile_id)
    )

    invalidated = evidence_repository.invalidate(
        evidence.evidence_id,
        reason="Source artifact failed manual review.",
    )

    assert invalidated is not None
    assert invalidated.lifecycle_state == EvidenceLifecycleState.INVALIDATED
    assert invalidated.superseded_by_evidence_id is None
    assert invalidated.lifecycle_reason == "Source artifact failed manual review."
    assert invalidated.result_summary == evidence.result_summary
    assert evidence_without_lifecycle_metadata(invalidated) == (
        evidence_without_lifecycle_metadata(evidence)
    )


def test_evidence_supersede_with_discovery_repository_flags_dependent_discovery(
    db_session,
) -> None:
    profile, hypothesis, evidence, discovery = create_evidence_bound_discovery(db_session)
    evidence_repository = EvidenceRepository(db_session)
    discovery_repository = DiscoveryRepository(db_session)
    replacement = evidence_repository.create(
        build_evidence(
            hypothesis.hypothesis_id,
            profile.profile_id,
            execution_run_ref="execution-run:replacement",
            provenance=EvidenceProvenance(
                analysis_frame_ref="analysis-frame:customers:v1:spend-churn",
                execution_run_ref="execution-run:replacement",
                code_reference="tests/evidence",
            ),
        )
    )
    original_discovery_payload = discovery_without_review_metadata(discovery)

    evidence_repository.supersede(
        evidence.evidence_id,
        replacement.evidence_id,
        reason="Corrected executor output supersedes this Evidence.",
        discovery_repository=discovery_repository,
    )

    flagged = discovery_repository.get_by_id(discovery.discovery_id)
    superseded = evidence_repository.get_by_id(evidence.evidence_id)

    assert flagged is not None
    assert superseded is not None
    assert flagged.lifecycle_state == DiscoveryLifecycleState.FLAGGED
    assert flagged.flagged_by_evidence_ids == [evidence.evidence_id]
    assert len(flagged.review_reasons) == 1
    assert str(evidence.evidence_id) in flagged.review_reasons[0]
    assert str(replacement.evidence_id) in flagged.review_reasons[0]
    assert "change_type=superseded" in flagged.review_reasons[0]
    assert discovery_without_review_metadata(flagged) == original_discovery_payload
    assert superseded.result_summary == evidence.result_summary


def test_evidence_supersede_rejects_discovery_repository_from_different_session(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'evidence_supersede_sessions.sqlite3').as_posix()}"
    create_db_engine.cache_clear()
    init_db(database_url)
    evidence_session = get_session(database_url)
    discovery_session = get_session(database_url)
    verification_session = get_session(database_url)
    try:
        profile, hypothesis, evidence, discovery = create_evidence_bound_discovery(evidence_session)
        evidence_repository = EvidenceRepository(evidence_session)
        replacement = evidence_repository.create(
            build_evidence(
                hypothesis.hypothesis_id,
                profile.profile_id,
                execution_run_ref="execution-run:replacement",
                provenance=EvidenceProvenance(
                    analysis_frame_ref="analysis-frame:customers:v1:spend-churn",
                    execution_run_ref="execution-run:replacement",
                    code_reference="tests/evidence",
                ),
            )
        )

        with pytest.raises(
            ValueError,
            match=(
                "Evidence lifecycle mutation and dependent Discovery flagging must "
                "use the same SQLModel session"
            ),
        ):
            evidence_repository.supersede(
                evidence.evidence_id,
                replacement.evidence_id,
                reason="This mutation must be rejected.",
                discovery_repository=DiscoveryRepository(discovery_session),
            )

        persisted_evidence = EvidenceRepository(verification_session).get_by_id(
            evidence.evidence_id
        )
        persisted_discovery = DiscoveryRepository(verification_session).get_by_id(
            discovery.discovery_id
        )

        assert persisted_evidence is not None
        assert persisted_discovery is not None
        assert persisted_evidence.lifecycle_state == EvidenceLifecycleState.ACTIVE
        assert persisted_evidence.superseded_by_evidence_id is None
        assert persisted_evidence.lifecycle_reason is None
        assert persisted_discovery.lifecycle_state == DiscoveryLifecycleState.ACTIVE
        assert persisted_discovery.review_reasons == []
        assert persisted_discovery.flagged_by_evidence_ids == []
    finally:
        evidence_session.close()
        discovery_session.close()
        verification_session.close()
        create_db_engine.cache_clear()


def test_evidence_invalidate_with_discovery_repository_flags_dependent_discovery(
    db_session,
) -> None:
    _, _, evidence, discovery = create_evidence_bound_discovery(db_session)
    evidence_repository = EvidenceRepository(db_session)
    discovery_repository = DiscoveryRepository(db_session)

    evidence_repository.invalidate(
        evidence.evidence_id,
        reason="Source artifact failed manual review.",
        discovery_repository=discovery_repository,
    )

    flagged = discovery_repository.get_by_id(discovery.discovery_id)

    assert flagged is not None
    assert flagged.lifecycle_state == DiscoveryLifecycleState.FLAGGED
    assert flagged.flagged_by_evidence_ids == [evidence.evidence_id]
    assert len(flagged.review_reasons) == 1
    assert str(evidence.evidence_id) in flagged.review_reasons[0]
    assert "change_type=invalidated" in flagged.review_reasons[0]
    assert "replacement_evidence_id" not in flagged.review_reasons[0]


def test_evidence_invalidate_rejects_discovery_repository_from_different_session(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'evidence_invalidate_sessions.sqlite3').as_posix()}"
    create_db_engine.cache_clear()
    init_db(database_url)
    evidence_session = get_session(database_url)
    discovery_session = get_session(database_url)
    verification_session = get_session(database_url)
    try:
        _, _, evidence, discovery = create_evidence_bound_discovery(evidence_session)
        evidence_repository = EvidenceRepository(evidence_session)

        with pytest.raises(
            ValueError,
            match=(
                "Evidence lifecycle mutation and dependent Discovery flagging must "
                "use the same SQLModel session"
            ),
        ):
            evidence_repository.invalidate(
                evidence.evidence_id,
                reason="This mutation must be rejected.",
                discovery_repository=DiscoveryRepository(discovery_session),
            )

        persisted_evidence = EvidenceRepository(verification_session).get_by_id(
            evidence.evidence_id
        )
        persisted_discovery = DiscoveryRepository(verification_session).get_by_id(
            discovery.discovery_id
        )

        assert persisted_evidence is not None
        assert persisted_discovery is not None
        assert persisted_evidence.lifecycle_state == EvidenceLifecycleState.ACTIVE
        assert persisted_evidence.superseded_by_evidence_id is None
        assert persisted_evidence.lifecycle_reason is None
        assert persisted_discovery.lifecycle_state == DiscoveryLifecycleState.ACTIVE
        assert persisted_discovery.review_reasons == []
        assert persisted_discovery.flagged_by_evidence_ids == []
    finally:
        evidence_session.close()
        discovery_session.close()
        verification_session.close()
        create_db_engine.cache_clear()


def test_evidence_lifecycle_without_discovery_repository_preserves_discovery_review_state(
    db_session,
) -> None:
    profile, hypothesis, evidence, discovery = create_evidence_bound_discovery(db_session)
    evidence_repository = EvidenceRepository(db_session)
    discovery_repository = DiscoveryRepository(db_session)
    replacement = evidence_repository.create(
        build_evidence(
            hypothesis.hypothesis_id,
            profile.profile_id,
            execution_run_ref="execution-run:replacement",
            provenance=EvidenceProvenance(
                analysis_frame_ref="analysis-frame:customers:v1:spend-churn",
                execution_run_ref="execution-run:replacement",
            ),
        )
    )
    _, _, invalidated_evidence, invalidated_discovery = create_evidence_bound_discovery(
        db_session,
        evidence_overrides={
            "execution_run_ref": "execution-run:invalidate-without-repository",
            "provenance": EvidenceProvenance(
                analysis_frame_ref="analysis-frame:customers:v1:spend-churn",
                execution_run_ref="execution-run:invalidate-without-repository",
            ),
        },
    )

    evidence_repository.supersede(
        evidence.evidence_id,
        replacement.evidence_id,
        reason="Corrected executor output supersedes this Evidence.",
    )
    evidence_repository.invalidate(
        invalidated_evidence.evidence_id,
        reason="Source artifact failed manual review.",
    )

    superseded_discovery = discovery_repository.get_by_id(discovery.discovery_id)
    invalidated_evidence_discovery = discovery_repository.get_by_id(
        invalidated_discovery.discovery_id
    )

    assert superseded_discovery is not None
    assert invalidated_evidence_discovery is not None
    assert superseded_discovery.lifecycle_state == DiscoveryLifecycleState.ACTIVE
    assert superseded_discovery.review_reasons == []
    assert invalidated_evidence_discovery.lifecycle_state == DiscoveryLifecycleState.ACTIVE
    assert invalidated_evidence_discovery.review_reasons == []


def test_discovery_that_does_not_reference_changed_evidence_is_not_flagged(
    db_session,
) -> None:
    profile, hypothesis, evidence, _ = create_evidence_bound_discovery(db_session)
    _, _, _, unrelated_discovery = create_evidence_bound_discovery(db_session)
    evidence_repository = EvidenceRepository(db_session)
    discovery_repository = DiscoveryRepository(db_session)
    replacement = evidence_repository.create(
        build_evidence(
            hypothesis.hypothesis_id,
            profile.profile_id,
            execution_run_ref="execution-run:replacement",
            provenance=EvidenceProvenance(
                analysis_frame_ref="analysis-frame:customers:v1:spend-churn",
                execution_run_ref="execution-run:replacement",
            ),
        )
    )

    evidence_repository.supersede(
        evidence.evidence_id,
        replacement.evidence_id,
        reason="Corrected executor output supersedes this Evidence.",
        discovery_repository=discovery_repository,
    )

    unrelated = discovery_repository.get_by_id(unrelated_discovery.discovery_id)

    assert unrelated is not None
    assert unrelated.lifecycle_state == DiscoveryLifecycleState.ACTIVE
    assert unrelated.review_reasons == []
    assert unrelated.flagged_by_evidence_ids == []


def test_repeated_discovery_flagging_does_not_duplicate_identical_review_reason(
    db_session,
) -> None:
    profile, hypothesis, evidence, discovery = create_evidence_bound_discovery(db_session)
    evidence_repository = EvidenceRepository(db_session)
    discovery_repository = DiscoveryRepository(db_session)
    replacement = evidence_repository.create(
        build_evidence(
            hypothesis.hypothesis_id,
            profile.profile_id,
            execution_run_ref="execution-run:replacement",
            provenance=EvidenceProvenance(
                analysis_frame_ref="analysis-frame:customers:v1:spend-churn",
                execution_run_ref="execution-run:replacement",
            ),
        )
    )

    for _ in range(2):
        discovery_repository.flag_by_evidence_change(
            evidence.evidence_id,
            "Corrected executor output supersedes this Evidence.",
            change_type=EvidenceLifecycleState.SUPERSEDED,
            replacement_evidence_id=replacement.evidence_id,
        )

    flagged = discovery_repository.get_by_id(discovery.discovery_id)

    assert flagged is not None
    assert flagged.lifecycle_state == DiscoveryLifecycleState.FLAGGED
    assert flagged.review_reasons == [
        (
            f"changed_evidence_id={evidence.evidence_id}; "
            "change_type=superseded; "
            f"replacement_evidence_id={replacement.evidence_id}; "
            "reason=Corrected executor output supersedes this Evidence."
        )
    ]
    assert flagged.flagged_by_evidence_ids == [evidence.evidence_id]


def test_discovery_review_flag_does_not_overwrite_terminal_review_state(
    db_session,
) -> None:
    _, _, evidence, discovery = create_evidence_bound_discovery(
        db_session,
        discovery_overrides={"lifecycle_state": DiscoveryLifecycleState.INVALIDATED},
    )
    discovery_repository = DiscoveryRepository(db_session)

    affected = discovery_repository.flag_by_evidence_change(
        evidence.evidence_id,
        "Corrected executor output supersedes this Evidence.",
        change_type=EvidenceLifecycleState.SUPERSEDED,
    )
    unchanged = discovery_repository.get_by_id(discovery.discovery_id)

    assert affected == []
    assert unchanged is not None
    assert unchanged.lifecycle_state == DiscoveryLifecycleState.INVALIDATED
    assert unchanged.review_reasons == []
    assert unchanged.flagged_by_evidence_ids == []


def test_data_profile_evidence_and_discovery_invariants_are_enforced() -> None:
    profile = build_data_profile()
    evidence = build_evidence(uuid4(), profile.profile_id)

    with pytest.raises(ValidationError):
        profile.row_count = 999

    with pytest.raises(ValidationError):
        evidence.result_summary = EvidenceResultSummary(summary="Edited interpretation.")

    with pytest.raises(ValidationError):
        Evidence(
            **(
                build_evidence(uuid4(), profile.profile_id).model_dump()
                | {
                    "provenance": EvidenceProvenance(
                        analysis_frame_ref="different-frame",
                        execution_run_ref="execution-run:001",
                    )
                }
            )
        )

    with pytest.raises(ValidationError):
        build_discovery(uuid4(), profile.profile_id, uuid4(), evidence_ids=[])

    with pytest.raises(ValidationError):
        EvidenceResultSummary(summary="There is no relationship between spend and churn.")

    careful_summary = EvidenceResultSummary(
        summary=(
            "Available evidence is insufficient to reject independence within scope using method M."
        )
    )
    assert "insufficient" in careful_summary.summary

    with pytest.raises(ValidationError):
        DiscoveryClaim(
            statement="No relationship exists between spend and churn.",
            scope="Active residential customers.",
        )


def test_hypothesis_repository_enforces_task_admission_and_cardinality(db_session) -> None:
    profile = DataProfileRepository(db_session).create(build_data_profile())
    draft_profile = DataProfileRepository(db_session).create(
        build_data_profile(
            dvc_hash="md5:customers-draft",
            dvc_version_label="customers-draft",
            lifecycle_state=DataProfileLifecycleState.DRAFT,
            accepted_as_ground_truth=False,
        )
    )
    task_repository = TaskRepository(db_session)
    hypothesis_repository = HypothesisRepository(db_session)

    proposed_task = task_repository.create(
        build_task(profile.profile_id, lifecycle_state=TaskLifecycleState.PROPOSED)
    )
    with pytest.raises(ValueError):
        hypothesis_repository.create(build_hypothesis(proposed_task.task_id, profile.profile_id))

    draft_profile_task = task_repository.create(build_task(draft_profile.profile_id))
    with pytest.raises(ValueError):
        hypothesis_repository.create(
            build_hypothesis(draft_profile_task.task_id, draft_profile.profile_id)
        )

    parent_task = task_repository.create(build_task(profile.profile_id))
    task_repository.create(build_task(profile.profile_id, parent_task_id=parent_task.task_id))
    with pytest.raises(ValueError):
        hypothesis_repository.create(build_hypothesis(parent_task.task_id, profile.profile_id))

    terminal_task = task_repository.create(build_task(profile.profile_id))
    hypothesis_repository.create(build_hypothesis(terminal_task.task_id, profile.profile_id))
    with pytest.raises(ValueError):
        hypothesis_repository.create(build_hypothesis(terminal_task.task_id, profile.profile_id))


def test_discovery_repository_enforces_evidence_ownership_and_cardinality(db_session) -> None:
    profile = DataProfileRepository(db_session).create(build_data_profile())
    task_repository = TaskRepository(db_session)
    hypothesis_repository = HypothesisRepository(db_session)
    evidence_repository = EvidenceRepository(db_session)
    discovery_repository = DiscoveryRepository(db_session)

    first_task = task_repository.create(build_task(profile.profile_id))
    second_task = task_repository.create(build_task(profile.profile_id))
    first_hypothesis = hypothesis_repository.create(
        build_hypothesis(first_task.task_id, profile.profile_id)
    )
    second_hypothesis = hypothesis_repository.create(
        build_hypothesis(second_task.task_id, profile.profile_id)
    )
    first_evidence = evidence_repository.create(
        build_evidence(first_hypothesis.hypothesis_id, profile.profile_id)
    )
    second_evidence = evidence_repository.create(
        build_evidence(second_hypothesis.hypothesis_id, profile.profile_id)
    )

    with pytest.raises(ValueError):
        discovery_repository.create(
            build_discovery(
                first_hypothesis.hypothesis_id,
                profile.profile_id,
                second_evidence.evidence_id,
            )
        )

    discovery_repository.create(
        build_discovery(
            first_hypothesis.hypothesis_id,
            profile.profile_id,
            first_evidence.evidence_id,
        )
    )
    with pytest.raises(ValueError):
        discovery_repository.create(
            build_discovery(
                first_hypothesis.hypothesis_id,
                profile.profile_id,
                first_evidence.evidence_id,
            )
        )

    third_task = task_repository.create(build_task(profile.profile_id))
    third_hypothesis = hypothesis_repository.create(
        build_hypothesis(third_task.task_id, profile.profile_id)
    )
    superseded_evidence = evidence_repository.create(
        build_evidence(
            third_hypothesis.hypothesis_id,
            profile.profile_id,
            lifecycle_state=EvidenceLifecycleState.SUPERSEDED,
        )
    )
    with pytest.raises(ValueError):
        discovery_repository.create(
            build_discovery(
                third_hypothesis.hypothesis_id,
                profile.profile_id,
                superseded_evidence.evidence_id,
            )
        )


def test_user_decision_is_typed_provenance_not_scientific_knowledge(db_session) -> None:
    repository = UserDecisionRepository(db_session)
    decision = repository.create(
        UserDecision(
            decision_type=UserDecisionType.VALIDATION_STRATEGY,
            decision="Use stratified validation split.",
            rationale="Protect minority churn cases.",
            alternatives_considered=["Random split"],
        )
    )

    assert repository.list(decision_type=UserDecisionType.VALIDATION_STRATEGY) == [decision]
    assert not hasattr(decision, "project_id")


def test_session_frame_repository_round_trip_is_workspace_local(db_session) -> None:
    objective = build_objective()
    frame = SessionFrameRepository(db_session).create(
        SessionFrame(
            frame_topic="churn-frame",
            frame_status=SessionFrameStatus.HANDOFF,
            objective_snapshot=objective.statement,
            created_at=datetime.now(UTC),
        )
    )

    assert SessionFrameRepository(db_session).get_latest() == frame
    assert SessionFrameRepository(db_session).list_recent(limit=1) == [frame]
    assert "project_id" not in SessionFrame.model_fields


def test_workspace_databases_are_isolated(tmp_path: Path) -> None:
    first_url = f"sqlite:///{(tmp_path / 'first.sqlite3').as_posix()}"
    second_url = f"sqlite:///{(tmp_path / 'second.sqlite3').as_posix()}"
    create_db_engine.cache_clear()
    init_db(first_url)
    init_db(second_url)

    first_session = get_session(first_url)
    second_session = get_session(second_url)
    try:
        created = ObjectiveRepository(first_session).create(build_objective(title="First"))

        assert ObjectiveRepository(first_session).get_by_id(created.objective_id) == created
        assert ObjectiveRepository(second_session).get_by_id(created.objective_id) is None
        assert ObjectiveRepository(second_session).list() == []
    finally:
        first_session.close()
        second_session.close()
        create_db_engine.cache_clear()


def test_append_only_repositories_do_not_expose_update(db_session) -> None:
    assert not hasattr(DataProfileRepository(db_session), "update")
    assert not hasattr(EvidenceRepository(db_session), "update")
    assert not hasattr(DiscoveryRepository(db_session), "update")
    assert not hasattr(SessionFrameRepository(db_session), "update")


def test_task_and_non_fco_generated_view_guards() -> None:
    inactive_task = build_task(uuid4(), lifecycle_state=TaskLifecycleState.PAUSED)
    proposed_task = build_task(uuid4(), lifecycle_state=TaskLifecycleState.PROPOSED)
    rejected_task = build_task(uuid4(), lifecycle_state=TaskLifecycleState.REJECTED)
    parent_task = build_task(
        uuid4(),
        task_kind=TaskKind.ORGANIZING,
        variables=[],
        evidence_expectation=None,
    )

    assert {"proposed", "rejected"} <= {item.value for item in TaskLifecycleState}
    assert inactive_task.can_generate_hypothesis() is False
    assert proposed_task.can_generate_hypothesis() is False
    assert rejected_task.can_generate_hypothesis() is False
    assert build_task(uuid4()).can_generate_hypothesis(has_child_tasks=True) is False
    assert parent_task.can_generate_hypothesis() is False
    assert "generated_view" not in {item.value for item in FirstClassObjectType}


def test_planner_and_executor_authoring_contracts() -> None:
    from agents.executor.types import ExecutorOutput
    from agents.planner.types import PlannerOutput

    planner_fields = set(PlannerOutput.model_fields)
    executor_fields = set(ExecutorOutput.model_fields)

    assert "evidence_drafts" not in planner_fields
    assert "discovery_drafts" not in planner_fields
    assert {"planner_operations", "executor_dispatch_ref"} <= planner_fields
    # ExecutorOutput remains a scaffold. Durable Evidence/Discovery admission
    # belongs to the planner operation boundary, not free-form agent output.
    assert {"evidence_drafts", "discovery_drafts", "execution_run_ref"}.isdisjoint(
        executor_fields
    )


def test_repository_queries_do_not_require_project_fco(db_session) -> None:
    older = DataProfileRepository(db_session).create(
        build_data_profile(created_at=datetime.now(UTC) - timedelta(days=1))
    )
    newer = DataProfileRepository(db_session).create(
        build_data_profile(
            dvc_hash="md5:customers-v2",
            dvc_version_label="customers-v2",
        )
    )

    assert DataProfileRepository(db_session).list_for_dataset_path("data/customers.csv") == [
        newer,
        older,
    ]
