"""Targeted upgrades for the durable execution-attempt protocol."""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from cognieda.infrastructure.persistence.models import (
    ExecutionApprovalRecord,
    ExecutionOutboxRecord,
)

_EXECUTION_RUN_COLUMNS = {
    "dispatch_idempotency_key": "TEXT",
    "worker_id": "TEXT",
    "lease_epoch": "INTEGER NOT NULL DEFAULT 0",
    "lease_acquired_at": "DATETIME",
    "lease_expires_at": "DATETIME",
    "attempt_version": "INTEGER NOT NULL DEFAULT 1",
    "previous_attempt_id": "CHAR(32)",
    "retry_reason": "TEXT",
    "retry_authorization_metadata": "JSON",
    "recovery_status": "TEXT",
}


def upgrade_execution_attempt_schema(engine: Engine) -> None:
    """Upgrade legacy SQLite runs without treating unsafe in-flight work as resumable."""

    if engine.dialect.name != "sqlite":
        return
    if "execution_runs" not in set(inspect(engine).get_table_names()):
        return

    existing = {column["name"] for column in inspect(engine).get_columns("execution_runs")}
    with engine.begin() as connection:
        for name, definition in _EXECUTION_RUN_COLUMNS.items():
            if name not in existing:
                connection.execute(
                    text(f"ALTER TABLE execution_runs ADD COLUMN {name} {definition}")
                )
        connection.execute(
            text(
                "UPDATE execution_runs SET status = 'abandoned' "
                "WHERE status IN ('pending', 'pending_approval', 'admitted', "
                "'dispatch_claimed', 'running')"
            )
        )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_execution_runs_previous_attempt_id "
                "ON execution_runs (previous_attempt_id) WHERE previous_attempt_id IS NOT NULL"
            )
        )

    ExecutionApprovalRecord.__table__.create(engine, checkfirst=True)
    ExecutionOutboxRecord.__table__.create(engine, checkfirst=True)


def upgrade_session_frame_scope_schema(engine: Engine) -> None:
    """Give legacy SQLite SessionFrame snapshots an explicit default scope."""

    if engine.dialect.name != "sqlite":
        return
    if "session_frames" not in set(inspect(engine).get_table_names()):
        return
    existing = {column["name"] for column in inspect(engine).get_columns("session_frames")}
    if "scope_key" in existing:
        return
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE session_frames ADD COLUMN scope_key "
                "TEXT NOT NULL DEFAULT 'default'"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_session_frames_scope_key "
                "ON session_frames (scope_key)"
            )
        )
