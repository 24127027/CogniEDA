"""SQLite DDL and trigger equivalence test for S3-B baseline safety."""

from __future__ import annotations

import hashlib
import json

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
S3A_SQLITE_MASTER_OBJECT_COUNT = 214
S3A_SQLITE_MASTER_SHA256 = (
    "265178b8fd1b9fdf1c84ec25e27019a84d66221e1b9c0d9ef99761d4e183c6ed"
)


def _normalize_sql(value: str | None) -> str | None:
    if value is None:
        return None
    return " ".join(value.split())


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

    # Compare the complete non-internal sqlite_master representation with the
    # independently captured S3-A baseline. SQLite-owned autoindexes are
    # excluded because their names begin with sqlite_ and are not user DDL.
    with engine.connect() as conn:
        objects = [
            {
                "type": row[0],
                "name": row[1],
                "table": row[2],
                "sql": _normalize_sql(row[3]),
            }
            for row in conn.execute(
                text(
                    """
                    SELECT type, name, tbl_name, sql
                    FROM sqlite_master
                    WHERE name NOT LIKE 'sqlite_%'
                    ORDER BY type, name, tbl_name
                    """
                )
            )
        ]
    encoded = json.dumps(
        objects,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    assert len(objects) == S3A_SQLITE_MASTER_OBJECT_COUNT
    assert hashlib.sha256(encoded).hexdigest() == S3A_SQLITE_MASTER_SHA256
    trigger_names = {
        item["name"]
        for item in objects
        if item["type"] == "trigger"
    }

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
    assert trigger_names == expected_triggers


def test_facade_table_count() -> None:
    """SQLModel metadata must register exactly 21 table=True classes."""

    table_models = [
        cls_name
        for cls_name in FACADE_EXPORTS
        if cls_name.endswith("Record") and cls_name != "TimestampedRecord"
    ]
    assert len(table_models) == 21
    assert sorted(SQLModel.metadata.tables.keys()) == EXPECTED_TABLES
