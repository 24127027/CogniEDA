"""Database initialization helpers for the workspace-local graph store."""

from __future__ import annotations

from sqlmodel import SQLModel

from db import models  # noqa: F401
from db.session import create_db_engine, get_database_url


def init_db(database_url: str | None = None) -> str:
    """Create all configured SQLModel tables and return the database URL used."""

    resolved_url = database_url or get_database_url()
    engine = create_db_engine(resolved_url)
    from db.migrations import (
        upgrade_discovery_admission_claim_schema,
        upgrade_evaluation_control_schema,
        upgrade_legacy_payloads_schema,
        upgrade_objective_lifecycle_schema,
        upgrade_pre_repair_database,
        upgrade_proposal_decision_schema,
        upgrade_task_motivation_schema,
        upgrade_task_review_schema,
        upgrade_validity_events_schema,
    )

    upgrade_pre_repair_database(engine)
    upgrade_objective_lifecycle_schema(engine)
    upgrade_task_motivation_schema(engine)
    upgrade_task_review_schema(engine)
    upgrade_evaluation_control_schema(engine)
    upgrade_proposal_decision_schema(engine)
    upgrade_validity_events_schema(engine)
    SQLModel.metadata.create_all(engine)
    # Package 5 integrity triggers reference the complete Discovery chain and
    # therefore must be installed only after every referenced table exists.
    upgrade_discovery_admission_claim_schema(engine)
    upgrade_legacy_payloads_schema(engine)

    return resolved_url


def main() -> None:
    """Initialize the configured local artifact database and print the target URL."""

    resolved_url = init_db()
    print(f"Initialized database at {resolved_url}")
