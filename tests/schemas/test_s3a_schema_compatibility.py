"""S3-A canonical-owner and serialization compatibility checks."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from schemas import enums
from schemas.common import (
    BaselineSummary,
    EvidenceProvenance,
    EvidenceResultSummary,
    SchemaSummary,
)
from schemas.evidence import Evidence
from schemas.execution import ExecutionRun
from schemas.research import DataProfile, Objective


def test_bounded_packages_reuse_the_single_canonical_enum_definitions() -> None:
    """Normalization must not create second enum identities for persisted values."""

    import schemas.evidence as evidence
    import schemas.execution as execution
    import schemas.research as research

    research_names = {
        "AnalysisIntent",
        "AssumptionSource",
        "AssumptionStatus",
        "AssumptionTestability",
        "ConfidenceLevel",
        "DataProfileLifecycleState",
        "DataProfileMethod",
        "DatasetSourceType",
        "HypothesisEvidenceOutcome",
        "HypothesisStatus",
        "LineageOperationType",
        "ObjectiveStatus",
        "SessionFrameStatus",
        "TaskDependencyType",
        "TaskKind",
        "TaskLifecycleState",
    }
    execution_names = {"ExecutionApprovalStatus", "ExecutionRunStatus"}
    evidence_names = {"EvidenceLifecycleState", "EvidenceType"}

    for package, names in (
        (research, research_names),
        (execution, execution_names),
        (evidence, evidence_names),
    ):
        for name in names:
            assert getattr(package, name) is getattr(enums, name)


def test_representative_model_dump_json_is_baseline_compatible() -> None:
    """Moved models retain the exact S2-B field names and enum JSON values."""

    created_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    objective = Objective(
        objective_id=UUID("00000000-0000-0000-0000-000000000001"),
        title="Title",
        statement="Statement",
        created_at=created_at,
        updated_at=created_at,
    )
    profile = DataProfile(
        profile_id=UUID("00000000-0000-0000-0000-000000000002"),
        dataset_path="data/input.csv",
        method=enums.DataProfileMethod.BASELINE_SUMMARY,
        schema_summary=SchemaSummary(column_order=["x"]),
        baseline_summary=BaselineSummary(column_names=["x"]),
        row_count=1,
        column_count=1,
        created_at=created_at,
    )
    run = ExecutionRun(
        execution_run_id=UUID("00000000-0000-0000-0000-000000000003"),
        status=enums.ExecutionRunStatus.ADMITTED,
        created_at=created_at,
    )
    evidence = Evidence(
        evidence_id=UUID("00000000-0000-0000-0000-000000000004"),
        hypothesis_id=UUID("00000000-0000-0000-0000-000000000005"),
        profile_id=profile.profile_id,
        analysis_frame_ref="frame",
        execution_run_ref=str(run.execution_run_id),
        evidence_type=enums.EvidenceType.STATISTICAL_TEST,
        method="test",
        provenance=EvidenceProvenance(
            analysis_frame_ref="frame",
            execution_run_ref=str(run.execution_run_id),
        ),
        result_summary=EvidenceResultSummary(
            summary="Observed p-value.",
            metric_name="p_value",
            metric_value=0.05,
        ),
        created_at=created_at,
    )

    assert objective.model_dump(mode="json") == {
        "objective_id": "00000000-0000-0000-0000-000000000001",
        "title": "Title",
        "statement": "Statement",
        "analysis_intent": "exploratory",
        "status": "active",
        "created_at": "2026-01-02T03:04:05Z",
        "updated_at": "2026-01-02T03:04:05Z",
    }
    assert profile.model_dump(mode="json")["method"] == "baseline_summary"
    assert run.model_dump(mode="json")["status"] == "admitted"
    assert evidence.model_dump(mode="json")["evidence_type"] == "statistical_test"


def test_moved_models_preserve_extra_forbid_and_immutability() -> None:
    """Pydantic configuration remains strict and immutable where it was at S2-B."""

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        Objective(title="Title", statement="Statement", unexpected=True)

    profile = DataProfile(
        dataset_path="data/input.csv",
        method=enums.DataProfileMethod.BASELINE_SUMMARY,
        schema_summary=SchemaSummary(column_order=["x"]),
        baseline_summary=BaselineSummary(column_names=["x"]),
        row_count=1,
        column_count=1,
    )
    with pytest.raises(ValidationError, match="Instance is frozen"):
        profile.row_count = 2
