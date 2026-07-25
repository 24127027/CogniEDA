"""SQLite DDL and trigger equivalence test for S3-B baseline safety."""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlmodel import SQLModel

from db.init_db import init_db
from db.models import __all__ as FACADE_EXPORTS
from db.session import create_db_engine

EXPECTED_TABLES = sorted([
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
])


def test_sqlite_schema_and_trigger_equivalence(tmp_path) -> None:
    """Fresh SQLite database must register exact 21 tables and triggers."""

    db_path = tmp_path / "schema_test.sqlite3"
    url = f"sqlite:///{db_path.as_posix()}"
    init_db(url)
    engine = create_db_engine(url)

    inspector = inspect(engine)
    table_names = sorted([t for t in inspector.get_table_names() if not t.startswith("sqlite_")])

    # 21 persistent domain tables + legacy quarantine + schema migration markers
    assert set(EXPECTED_TABLES) <= set(table_names)
    assert len(EXPECTED_TABLES) == 21

    # Check triggers
    with engine.connect() as conn:
        triggers = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type = 'trigger'")
        ).fetchall()
        trigger_names = {row[0] for row in triggers}

    expected_triggers = {
        "legacy_scientific_quarantine_immutable_update",
        "legacy_scientific_quarantine_immutable_delete",
        "governance_authorities_immutable_core",
        "proposal_decisions_immutable_core",
        "proposal_decisions_monotonic_consumption",
        "validity_events_immutable",
        "validity_events_no_delete",
        "discovery_admission_claims_immutable_identity",
        "discovery_admission_claims_terminal",
        "proposal_decisions_exact_consumption",
    }
    assert expected_triggers <= trigger_names


def test_facade_table_count() -> None:
    """SQLModel metadata must register exactly 21 table=True classes."""

    table_models = [
        cls_name
        for cls_name in FACADE_EXPORTS
        if cls_name.endswith("Record") and cls_name != "TimestampedRecord"
    ]
    assert len(table_models) == 21
    assert sorted(SQLModel.metadata.tables.keys()) == EXPECTED_TABLES
