from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from db.init_db import init_db
from db.session import create_db_engine, get_session
from repositories import (
    AssumptionRepository,
    AssumptionUpdate,
    DataProfileRepository,
    DiscoveryRepository,
    EvidenceRepository,
    HypothesisRepository,
    HypothesisUpdate,
    ObjectiveRepository,
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
    AssumptionStatus,
    ConfidenceLevel,
    DataProfileLifecycleState,
    DataProfileMethod,
    DiscoveryEpistemicStatus,
    EvidenceType,
    FirstClassObjectType,
    HypothesisStatus,
    ObjectiveStatus,
    QualityFlagSeverity,
    SessionFrameStatus,
    TaskKind,
    TaskLifecycleState,
    UserDecisionType,
)


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


def build_assumption(**overrides: object) -> Assumption:
    payload: dict[str, object] = {
        "statement": "Each row represents one customer.",
        "basis": "Derived from unique customer identifier checks.",
        "confidence": ConfidenceLevel.MEDIUM,
        "status": AssumptionStatus.ACTIVE,
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
            decision_rule="p_value < alpha",
            strength="moderate",
            uncertainty="p_value=0.01",
            invalidators=["DataProfile superseded", "method implementation changes"],
        ),
    }
    payload.update(overrides)
    return Discovery(**payload)


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


def test_assumption_repository_is_planning_scoped_by_profile(db_session) -> None:
    profile = DataProfileRepository(db_session).create(build_data_profile())
    repository = AssumptionRepository(db_session)

    active = repository.create(build_assumption(profile_id=profile.profile_id))
    repository.create(build_assumption(statement="Archived", status=AssumptionStatus.ARCHIVED))
    updated = repository.update(
        active.assumption_id,
        AssumptionUpdate(status=AssumptionStatus.VALIDATED),
    )

    assert updated is not None
    assert updated.status == AssumptionStatus.VALIDATED
    assert repository.list_active() == []
    assert repository.list_for_profile(profile.profile_id) == [updated]


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
    updated_hypothesis = hypothesis_repository.update(
        hypothesis.hypothesis_id,
        HypothesisUpdate(status=HypothesisStatus.COMPLETED),
    )

    assert evidence.profile_id == profile.profile_id
    assert evidence.analysis_frame_ref == "analysis-frame:customers:v1:spend-churn"
    assert evidence.execution_run_ref == "execution-run:001"
    assert discovery.evidence_ids == [evidence.evidence_id]
    assert discovery.validity_basis.data_profile_id == profile.profile_id
    assert discovery.validity_basis.assumptions_excluded_from_inference is True
    assert discovery_repository.list_for_hypothesis(hypothesis.hypothesis_id) == [discovery]
    assert updated_hypothesis is not None
    assert updated_hypothesis.status == HypothesisStatus.COMPLETED


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
                build_evidence(uuid4(), profile.profile_id)
                .model_dump()
                | {"provenance": EvidenceProvenance(
                    analysis_frame_ref="different-frame",
                    execution_run_ref="execution-run:001",
                )}
            )
        )

    with pytest.raises(ValidationError):
        build_discovery(uuid4(), profile.profile_id, uuid4(), evidence_ids=[])


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
    parent_task = build_task(
        uuid4(),
        task_kind=TaskKind.ORGANIZING,
        variables=[],
        evidence_expectation=None,
    )

    assert "proposed" not in {item.value for item in TaskLifecycleState}
    assert inactive_task.can_generate_hypothesis() is False
    assert parent_task.can_generate_hypothesis() is False
    assert "generated_view" not in {item.value for item in FirstClassObjectType}


def test_planner_and_executor_authoring_contracts() -> None:
    from agents.hypothesis_analyst.types import ExecutorOutput
    from agents.planner.types import PlannerOutput

    planner_fields = set(PlannerOutput.model_fields)
    executor_fields = set(ExecutorOutput.model_fields)

    assert "evidence_drafts" not in planner_fields
    assert "discovery_drafts" not in planner_fields
    assert {"planner_operations", "executor_dispatch_ref"} <= planner_fields
    assert {"evidence_drafts", "discovery_drafts", "execution_run_ref"} <= executor_fields


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
