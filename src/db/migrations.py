"""Targeted, idempotent upgrades for workspace-local graph databases."""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from db.models import ExecutionApprovalRecord, ExecutionInboxRecord, ExecutionOutboxRecord

_EXECUTION_RUN_COLUMNS = {
    "dispatch_idempotency_key": "VARCHAR",
    "worker_id": "VARCHAR",
    "lease_epoch": "INTEGER NOT NULL DEFAULT 0",
    "lease_acquired_at": "DATETIME",
    "lease_expires_at": "DATETIME",
    "attempt_version": "INTEGER NOT NULL DEFAULT 1",
    "finalizer_owner_id": "VARCHAR",
    "finalization_fencing_epoch": "INTEGER",
    "finalization_claimed_at": "DATETIME",
    "finalization_expires_at": "DATETIME",
    "previous_attempt_id": "CHAR(32)",
    "retry_reason": "TEXT",
    "retry_authorization_metadata": "JSON",
    "recovery_status": "TEXT",
}

_EXECUTION_RUN_INDEXES = {
    "ix_execution_runs_task_id": "task_id",
    "ix_execution_runs_hypothesis_id": "hypothesis_id",
    "ix_execution_runs_analysis_frame_id": "analysis_frame_id",
    "ix_execution_runs_executor_type": "executor_type",
    "ix_execution_runs_method_id": "method_id",
    "ix_execution_runs_parameter_hash": "parameter_hash",
    "ix_execution_runs_status": "status",
    "ix_execution_runs_dispatch_idempotency_key": "dispatch_idempotency_key",
    "ix_execution_runs_worker_id": "worker_id",
    "ix_execution_runs_finalizer_owner_id": "finalizer_owner_id",
    "ix_execution_runs_previous_attempt_id": "previous_attempt_id",
    "ix_execution_runs_created_at": "created_at",
}


def upgrade_pre_repair_database(engine: Engine) -> None:
    """Upgrade an existing pre-repair schema without relying on ``create_all``.

    Clean installations are created by ``init_db`` after this targeted upgrade.
    Existing databases retain all scientific records; legacy in-flight runs are
    marked ``abandoned`` because their old schema contains neither a durable
    dispatch key nor a fencing epoch and therefore cannot be resumed safely.
    """

    if engine.dialect.name != "sqlite":
        raise ValueError(
            "Execution-attempt schema migration supports SQLite only; "
            f"received {engine.dialect.name!r}."
        )

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "execution_runs" in tables:
        existing_columns = {column["name"] for column in inspector.get_columns("execution_runs")}
        with engine.begin() as connection:
            for name, definition in _EXECUTION_RUN_COLUMNS.items():
                if name not in existing_columns:
                    connection.execute(
                        text(f"ALTER TABLE execution_runs ADD COLUMN {name} {definition}")
                    )
            connection.execute(
                text(
                    "UPDATE execution_runs SET status = 'abandoned' "
                    "WHERE status IN ("
                    "'pending', 'running', 'pending_approval', 'admitted', 'dispatch_claimed'"
                    ")"
                )
            )
            for index_name, column_name in _EXECUTION_RUN_INDEXES.items():
                connection.execute(
                    text(
                        f"CREATE INDEX IF NOT EXISTS {index_name} ON execution_runs ({column_name})"
                    )
                )
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS "
                    "uq_execution_runs_previous_attempt_id "
                    "ON execution_runs (previous_attempt_id) "
                    "WHERE previous_attempt_id IS NOT NULL"
                )
            )

    # These are new protocol-side tables.  Creating only the missing tables is
    # safe for an existing database and does not paper over changed old tables.
    ExecutionApprovalRecord.__table__.create(engine, checkfirst=True)
    ExecutionOutboxRecord.__table__.create(engine, checkfirst=True)
    ExecutionInboxRecord.__table__.create(engine, checkfirst=True)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS "
                "uq_execution_outbox_execution_run_id "
                "ON execution_outbox (execution_run_id)"
            )
        )


def upgrade_task_motivation_schema(engine: Engine) -> None:
    """Upgrade Tasks schema to include motivated_by_discovery_ids.

    Adds a JSON column initialized to an empty list '[]' for all existing tasks.
    """

    if engine.dialect.name != "sqlite":
        raise ValueError(
            "Task motivation schema migration supports SQLite only; "
            f"received {engine.dialect.name!r}."
        )

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "tasks" in tables:
        existing_columns = {column["name"] for column in inspector.get_columns("tasks")}
        if "motivated_by_discovery_ids" not in existing_columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE tasks ADD COLUMN motivated_by_discovery_ids "
                        "JSON NOT NULL DEFAULT '[]'"
                    )
                )


def downgrade_task_motivation_schema(engine: Engine) -> None:
    """Downgrade Tasks schema by removing motivated_by_discovery_ids."""

    if engine.dialect.name != "sqlite":
        raise ValueError(
            "Task motivation schema migration supports SQLite only; "
            f"received {engine.dialect.name!r}."
        )

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "tasks" in tables:
        existing_columns = {column["name"] for column in inspector.get_columns("tasks")}
        if "motivated_by_discovery_ids" in existing_columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE tasks DROP COLUMN motivated_by_discovery_ids")
                )


def upgrade_task_review_schema(engine: Engine) -> None:
    """Upgrade Tasks schema with idempotent planning-review reasons."""

    if engine.dialect.name != "sqlite":
        raise ValueError(
            "Task review schema migration supports SQLite only; "
            f"received {engine.dialect.name!r}."
        )
    inspector = inspect(engine)
    if "tasks" not in set(inspector.get_table_names()):
        return
    columns = {column["name"] for column in inspector.get_columns("tasks")}
    if "review_reasons" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE tasks ADD COLUMN review_reasons JSON NOT NULL DEFAULT '[]'")
            )
