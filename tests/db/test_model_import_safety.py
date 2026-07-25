"""Fresh-process import-order and metadata safety for the db.models facade."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

EXPECTED_TABLES = [
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
]


@pytest.mark.parametrize(
    "module_order",
    [
        ("db.models",),
        (
            "db.models.research",
            "db.models.execution",
            "db.models.evidence",
            "db.models",
        ),
        (
            "db.models.execution",
            "db.models.evidence",
            "db.models.research",
            "db.models",
        ),
        (
            "db.models.evidence",
            "db.models.research",
            "db.models.execution",
            "db.models",
        ),
    ],
)
def test_fresh_process_import_orders_register_the_exact_table_set(
    module_order: tuple[str, ...],
) -> None:
    """Every supported import order must register exactly the facade table set."""

    script = (
        "import importlib, json\n"
        f"for name in {module_order!r}: importlib.import_module(name)\n"
        "from sqlmodel import SQLModel\n"
        "print(json.dumps(sorted(SQLModel.metadata.tables)))\n"
    )
    environment = os.environ.copy()
    source_path = str(Path("src").resolve())
    environment["PYTHONPATH"] = os.pathsep.join(
        item for item in (source_path, environment.get("PYTHONPATH", "")) if item
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert json.loads(completed.stdout) == EXPECTED_TABLES


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
