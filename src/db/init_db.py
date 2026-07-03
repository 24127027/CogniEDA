"""Database initialization helpers for the workspace-local graph store."""

from __future__ import annotations

from sqlmodel import SQLModel

from db import models  # noqa: F401
from db.session import create_db_engine, get_database_url


def init_db(database_url: str | None = None) -> str:
    """Create all configured SQLModel tables and return the database URL used."""

    resolved_url = database_url or get_database_url()
    engine = create_db_engine(resolved_url)
    SQLModel.metadata.create_all(engine)
    return resolved_url


def main() -> None:
    """Initialize the configured local artifact database and print the target URL."""

    resolved_url = init_db()
    print(f"Initialized database at {resolved_url}")
