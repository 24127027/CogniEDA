"""Targeted, idempotent upgrades for workspace-local graph databases."""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlmodel import SQLModel

from db.models import (
    DiscoveryAdmissionClaimRecord,
    EvaluationControlRecord,
    ExecutionApprovalRecord,
    ExecutionInboxRecord,
    ExecutionOutboxRecord,
    GovernanceAuthorityRecord,
    ProposalDecisionRecord,
    ValidityEventRecord,
)

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
    "validity_state": "VARCHAR NOT NULL DEFAULT 'UNVERIFIED'",
    "validity_reason": "TEXT",
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
    "ix_execution_runs_validity_state": "validity_state",
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


def upgrade_objective_lifecycle_schema(engine: Engine) -> None:
    """Install active cardinality and preserve compatible revision history."""

    if engine.dialect.name != "sqlite":
        raise ValueError(
            f"Objective lifecycle migration supports SQLite only; received {engine.dialect.name!r}."
        )

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "objectives" not in tables:
        return

    with engine.begin() as connection:
        # SQLite refuses this statement when legacy data contains more than one
        # ACTIVE row. That explicit failure is safer than silently choosing one.
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_active_objective "
                "ON objectives (status) WHERE status = 'ACTIVE'"
            )
        )

    if "objective_revisions" not in tables:
        SQLModel.metadata.tables["objective_revisions"].create(engine, checkfirst=True)
        return

    columns = {column["name"] for column in inspector.get_columns("objective_revisions")}
    foreign_keys = inspector.get_foreign_keys("objective_revisions")
    if not any(
        key.get("referred_table") == "objectives"
        and key.get("constrained_columns") == ["objective_id"]
        for key in foreign_keys
    ):
        raise ValueError(
            "Existing objective_revisions table lacks its Objective foreign key; "
            "repair is required."
        )
    legacy_mappings = {
        "previous_statement": "previous_description",
        "previous_status": "previous_lifecycle_state",
        "new_statement": "new_description",
        "new_status": "new_lifecycle_state",
        "reason": "revision_reason",
        "actor": "created_by",
    }
    with engine.begin() as connection:
        for target, source in legacy_mappings.items():
            if target in columns:
                continue
            if source not in columns:
                raise ValueError(
                    "Existing objective_revisions table cannot be upgraded without "
                    f"source column {source!r}."
                )
            sql_type = "TEXT" if target not in {"previous_status", "new_status"} else "VARCHAR"
            connection.execute(
                text(f"ALTER TABLE objective_revisions ADD COLUMN {target} {sql_type}")
            )
            connection.execute(text(f"UPDATE objective_revisions SET {target} = {source}"))

        malformed = connection.execute(
            text(
                "SELECT COUNT(*) FROM objective_revisions WHERE "
                "previous_statement IS NULL OR trim(previous_statement) = '' OR "
                "new_statement IS NULL OR trim(new_statement) = '' OR "
                "previous_status IS NULL OR new_status IS NULL OR "
                "reason IS NULL OR trim(reason) = '' OR "
                "actor IS NULL OR trim(actor) = ''"
            )
        ).scalar_one()
        if malformed:
            raise ValueError(
                "Existing objective_revisions contains malformed rows; repair is required."
            )
        for index_name, column_name in {
            "ix_objective_revisions_objective_id": "objective_id",
            "ix_objective_revisions_created_at": "created_at",
            "ix_objective_revisions_planner_operation_id": "planner_operation_id",
            "ix_objective_revisions_user_decision_id": "user_decision_id",
        }.items():
            connection.execute(
                text(
                    f"CREATE INDEX IF NOT EXISTS {index_name} "
                    f"ON objective_revisions ({column_name})"
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
                connection.execute(text("ALTER TABLE tasks DROP COLUMN motivated_by_discovery_ids"))


def upgrade_task_review_schema(engine: Engine) -> None:
    """Upgrade Tasks schema with idempotent planning-review reasons."""

    if engine.dialect.name != "sqlite":
        raise ValueError(
            f"Task review schema migration supports SQLite only; received {engine.dialect.name!r}."
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


def upgrade_evaluation_control_schema(engine: Engine) -> None:
    """Ensure evaluation_controls table and new columns/indexes exist."""

    if engine.dialect.name != "sqlite":
        raise ValueError(
            "Evaluation control schema migration supports SQLite only; "
            f"received {engine.dialect.name!r}."
        )

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "evaluation_controls" not in tables:
        EvaluationControlRecord.__table__.create(engine, checkfirst=True)
        return

    columns = {column["name"] for column in inspector.get_columns("evaluation_controls")}
    additions = {
        "evidence_set_digest": "VARCHAR NOT NULL DEFAULT 'legacy-unverified'",
        "evaluation_key": "VARCHAR NOT NULL DEFAULT ''",
        "serialized_manifest": "JSON NOT NULL DEFAULT '{}'",
        "serialized_failure": "JSON",
    }
    with engine.begin() as connection:
        for name, definition in additions.items():
            if name not in columns:
                connection.execute(
                    text(f"ALTER TABLE evaluation_controls ADD COLUMN {name} {definition}")
                )
        connection.execute(
            text(
                "UPDATE evaluation_controls "
                "SET evaluation_key = 'legacy:' || evaluation_id, "
                "state = 'CONFLICT', "
                "failure_reason = COALESCE(failure_reason, 'legacy_incomplete_control') "
                "WHERE evaluation_key = ''"
            )
        )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS "
                "uq_evaluation_controls_bundle_identity "
                "ON evaluation_controls (hypothesis_id, bundle_digest, contract_version)"
            )
        )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_evaluation_controls_evaluation_key "
                "ON evaluation_controls (evaluation_key)"
            )
        )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS "
                "uq_evaluation_controls_active_hypothesis "
                "ON evaluation_controls (hypothesis_id) "
                "WHERE state IN ('PENDING', 'CLAIMED', 'PROPOSAL_READY', 'RETRYABLE_FAILED')"
            )
        )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_evaluation_controls_proposal_digest "
                "ON evaluation_controls (proposal_digest) WHERE proposal_digest IS NOT NULL"
            )
        )


def upgrade_proposal_decision_schema(engine: Engine) -> None:
    """Install durable authority/decision tables and immutable-decision guards."""

    if engine.dialect.name != "sqlite":
        raise ValueError(
            "Proposal decision schema migration supports SQLite only; "
            f"received {engine.dialect.name!r}."
        )
    GovernanceAuthorityRecord.__table__.create(engine, checkfirst=True)

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "proposal_decisions" in tables:
        required_columns = {
            "authority_id",
            "evaluation_key",
            "evidence_set_digest",
            "workspace_id",
            "purpose",
            "operation_type",
        }
        columns = {column["name"] for column in inspector.get_columns("proposal_decisions")}
        if not required_columns.issubset(columns):
            legacy_table = "proposal_decisions_legacy_unverified"
            if legacy_table in tables:
                raise ValueError(
                    "Legacy proposal decisions cannot be migrated while the quarantine table "
                    f"{legacy_table!r} already exists."
                )
            with engine.begin() as connection:
                connection.execute(text(f"ALTER TABLE proposal_decisions RENAME TO {legacy_table}"))

    ProposalDecisionRecord.__table__.create(engine, checkfirst=True)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TRIGGER IF NOT EXISTS governance_authorities_immutable_core "
                "BEFORE UPDATE OF "
                "authority_id, actor_identity, authority_class, workspace_id, session_id, "
                "purpose, operation_type, issued_by, issued_at, expires_at, "
                "authority_fingerprint, created_at "
                "ON governance_authorities "
                "BEGIN "
                "SELECT RAISE(ABORT, 'governance authority core is immutable'); "
                "END"
            )
        )
        connection.execute(
            text(
                "CREATE TRIGGER IF NOT EXISTS proposal_decisions_immutable_core "
                "BEFORE UPDATE OF "
                "decision_id, authority_id, evaluation_id, evaluation_key, hypothesis_id, "
                "task_id, proposal_digest, bundle_digest, evidence_set_digest, decision, actor, "
                "actor_authority_type, workspace_id, session_id, purpose, operation_type, "
                "decision_timestamp, reason, decision_fingerprint, created_at "
                "ON proposal_decisions "
                "BEGIN "
                "SELECT RAISE(ABORT, 'proposal decision core is immutable'); "
                "END"
            )
        )
        connection.execute(
            text(
                "CREATE TRIGGER IF NOT EXISTS proposal_decisions_monotonic_consumption "
                "BEFORE UPDATE OF consumed, consumed_at, consumed_by ON proposal_decisions "
                "WHEN NOT ("
                "OLD.consumed = 0 AND NEW.consumed = 1 "
                "AND NEW.consumed_at IS NOT NULL AND NEW.consumed_by IS NOT NULL"
                ") "
                "BEGIN "
                "SELECT RAISE(ABORT, 'proposal decision consumption is one-way'); "
                "END"
            )
        )


def upgrade_validity_events_schema(engine: Engine) -> None:
    """Install validity metadata and quarantine unverifiable legacy events."""

    if engine.dialect.name != "sqlite":
        raise ValueError(
            "Validity events schema migration supports SQLite only; "
            f"received {engine.dialect.name!r}."
        )
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    additions = {
        "data_profiles": {
            "lifecycle_reason": "TEXT",
        },
        "hypotheses": {
            "review_reasons": "JSON NOT NULL DEFAULT '[]'",
        },
        "analysis_frames": {
            "validity_state": "VARCHAR NOT NULL DEFAULT 'UNVERIFIED'",
            "validity_reason": "TEXT",
        },
    }
    with engine.begin() as connection:
        for table_name, columns_to_add in additions.items():
            if table_name not in tables:
                continue
            existing = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, definition in columns_to_add.items():
                if column_name not in existing:
                    connection.execute(
                        text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")
                    )
        if "analysis_frames" in tables:
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_analysis_frames_validity_state "
                    "ON analysis_frames (validity_state)"
                )
            )

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "validity_events" in tables:
        required_columns = {
            "authority_id",
            "replacement_fingerprint",
            "expected_source_state",
            "source_post_state",
            "plan_fingerprint",
            "affected_targets",
        }
        existing = {column["name"] for column in inspector.get_columns("validity_events")}
        if not required_columns.issubset(existing):
            quarantine_table = "validity_events_legacy_unverified"
            if quarantine_table in tables:
                raise ValueError(
                    "Legacy validity events cannot be migrated while quarantine table "
                    f"{quarantine_table!r} already exists."
                )
            with engine.begin() as connection:
                connection.execute(
                    text(f"ALTER TABLE validity_events RENAME TO {quarantine_table}")
                )

    ValidityEventRecord.__table__.create(engine, checkfirst=True)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TRIGGER IF NOT EXISTS validity_events_immutable "
                "BEFORE UPDATE ON validity_events "
                "BEGIN "
                "SELECT RAISE(ABORT, 'validity event is immutable'); "
                "END"
            )
        )
        connection.execute(
            text(
                "CREATE TRIGGER IF NOT EXISTS validity_events_no_delete "
                "BEFORE DELETE ON validity_events "
                "BEGIN "
                "SELECT RAISE(ABORT, 'validity event is immutable'); "
                "END"
            )
        )


def upgrade_discovery_admission_claim_schema(engine: Engine) -> None:
    """Install or upgrade fenced Discovery-admission control and replay guards."""

    if engine.dialect.name != "sqlite":
        raise ValueError(
            "Discovery admission claim schema migration supports SQLite only; "
            f"received {engine.dialect.name!r}."
        )

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "discoveries" in tables:
        discovery_columns = {column["name"] for column in inspector.get_columns("discoveries")}
        if "limitations" not in discovery_columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE discoveries ADD COLUMN limitations JSON NOT NULL DEFAULT '[]'"
                    )
                )

    if "discovery_admission_claims" in tables:
        columns = {column["name"] for column in inspector.get_columns("discovery_admission_claims")}
        additions = {
            "claim_token_digest": "VARCHAR",
            "discovery_id": "CHAR(32)",
            "discovery_fingerprint": "VARCHAR",
            "session_frame_id": "CHAR(32)",
            "session_frame_fingerprint": "VARCHAR",
            "committed_at": "DATETIME",
        }
        with engine.begin() as connection:
            for name, definition in additions.items():
                if name not in columns:
                    connection.execute(
                        text(
                            f"ALTER TABLE discovery_admission_claims ADD COLUMN {name} {definition}"
                        )
                    )
            connection.execute(
                text(
                    "UPDATE discovery_admission_claims "
                    "SET state = 'CONFLICT', "
                    "invalidation_reason = "
                    "'legacy Package 5 claim lacks fenced replay authority' "
                    "WHERE state IN ('PENDING', 'CLAIMED', 'COMMITTED') "
                    "AND (claim_token_digest IS NULL OR "
                    "(state = 'COMMITTED' AND (discovery_id IS NULL "
                    "OR discovery_fingerprint IS NULL OR session_frame_id IS NULL "
                    "OR session_frame_fingerprint IS NULL OR committed_at IS NULL)))"
                )
            )

    DiscoveryAdmissionClaimRecord.__table__.create(engine, checkfirst=True)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS "
                "uq_discovery_admission_claims_decision "
                "ON discovery_admission_claims (decision_id)"
            )
        )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS "
                "uq_discovery_admission_claims_discovery "
                "ON discovery_admission_claims (discovery_id) "
                "WHERE discovery_id IS NOT NULL"
            )
        )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS "
                "uq_discovery_admission_claims_session_frame "
                "ON discovery_admission_claims (session_frame_id) "
                "WHERE session_frame_id IS NOT NULL"
            )
        )
        connection.execute(
            text(
                "CREATE TRIGGER IF NOT EXISTS discovery_admission_claims_immutable_identity "
                "BEFORE UPDATE OF claim_id, evaluation_id, decision_id, proposal_digest, "
                "bundle_digest, admission_fingerprint, created_at "
                "ON discovery_admission_claims "
                "BEGIN "
                "SELECT RAISE(ABORT, 'discovery admission claim identity is immutable'); "
                "END"
            )
        )
        connection.execute(
            text(
                "CREATE TRIGGER IF NOT EXISTS discovery_admission_claims_terminal "
                "BEFORE UPDATE ON discovery_admission_claims "
                "WHEN OLD.state IN ('COMMITTED', 'CONFLICT', 'CANCELLED', 'INVALIDATED') "
                "BEGIN "
                "SELECT RAISE(ABORT, 'discovery admission claim is terminal'); "
                "END"
            )
        )
        connection.execute(
            text(
                "CREATE TRIGGER IF NOT EXISTS proposal_decisions_exact_consumption "
                "BEFORE UPDATE OF consumed, consumed_at, consumed_by ON proposal_decisions "
                "WHEN NEW.consumed = 1 AND NOT ("
                "EXISTS (SELECT 1 FROM discoveries d "
                "WHERE d.discovery_id = replace(NEW.consumed_by, '-', '') "
                "AND d.hypothesis_id = NEW.hypothesis_id) "
                "AND EXISTS (SELECT 1 FROM discovery_admission_claims c "
                "WHERE c.decision_id = NEW.decision_id "
                "AND c.evaluation_id = NEW.evaluation_id "
                "AND c.discovery_id = replace(NEW.consumed_by, '-', '') "
                "AND c.state = 'COMMITTED')"
                ") "
                "BEGIN "
                "SELECT RAISE(ABORT, 'proposal decision consumption lacks exact committed chain'); "
                "END"
            )
        )


def upgrade_legacy_payloads_schema(engine: Engine) -> None:
    """Migrate legacy durable payloads, runs, and terminal hypotheses."""

    from sqlmodel import Session

    from db.legacy_migration import LegacyPayloadMigrator

    with Session(engine) as session:
        migrator = LegacyPayloadMigrator(session)
        migrator.migrate_all()
