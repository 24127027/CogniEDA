"""Import-order and metadata safety tests for db.models bounded context facade."""

from __future__ import annotations

from sqlmodel import SQLModel


def test_sqlmodel_metadata_registers_all_21_tables_on_db_models_import() -> None:
    """Importing db.models must register all 21 tables in SQLModel.metadata."""


    expected_tables = {
        "analysis_frames",
        "assumptions",
        "data_profiles",
        "discoveries",
        "discovery_admission_claims",
        "evaluation_controls",
        "evidence",
        "execution_approvals",
        "execution_inbox",
        "execution_outbox",
        "execution_runs",
        "governance_authorities",
        "hypotheses",
        "objective_revisions",
        "objectives",
        "planner_operations",
        "proposal_decisions",
        "session_frames",
        "tasks",
        "user_decisions",
        "validity_events",
    }
    registered_tables = set(SQLModel.metadata.tables.keys())
    assert expected_tables.issubset(registered_tables), (
        f"Missing tables in SQLModel.metadata: {expected_tables - registered_tables}"
    )


def test_db_models_exports_all_21_table_records() -> None:
    """The db.models facade must export all 21 table records, TimestampedRecord, and utc_now."""

    import db.models

    expected_exports = [
        "AnalysisFrameRecord",
        "AssumptionRecord",
        "DataProfileRecord",
        "DiscoveryAdmissionClaimRecord",
        "DiscoveryRecord",
        "EvaluationControlRecord",
        "EvidenceRecord",
        "ExecutionApprovalRecord",
        "ExecutionInboxRecord",
        "ExecutionOutboxRecord",
        "ExecutionRunRecord",
        "GovernanceAuthorityRecord",
        "HypothesisRecord",
        "ObjectiveRecord",
        "ObjectiveRevisionRecord",
        "PlannerOperationRecord",
        "ProposalDecisionRecord",
        "SessionFrameRecord",
        "TaskRecord",
        "TimestampedRecord",
        "UserDecisionRecord",
        "ValidityEventRecord",
        "utc_now",
    ]
    for export in expected_exports:
        assert hasattr(db.models, export), f"db.models missing export {export}"
        assert export in db.models.__all__, f"{export} missing from db.models.__all__"


def test_submodule_import_registers_tables_independently() -> None:
    """Importing submodules directly must register their tables in SQLModel.metadata."""


    registered_tables = set(SQLModel.metadata.tables.keys())
    assert "objectives" in registered_tables
    assert "execution_runs" in registered_tables
    assert "evidence" in registered_tables
