"""Database settings, engine creation, and session management."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine

DEFAULT_SQLITE_PATH = Path(__file__).resolve().parents[2] / ".local" / "cognieda_graph.sqlite3"


def get_default_sqlite_url() -> str:
    """Return the default workspace-local SQLite URL for graph persistence."""

    return f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"


def get_database_url() -> str:
    """Return the configured database URL or the default local SQLite URL."""

    return os.getenv("COGNIEDA_DB_URL", "").strip() or get_default_sqlite_url()


def is_sqlite_url(database_url: str) -> bool:
    """Return whether a database URL points to SQLite."""

    return database_url.startswith("sqlite:")


def ensure_sqlite_directory(database_url: str) -> None:
    """Create the parent directory for the local SQLite file when needed."""

    if not is_sqlite_url(database_url):
        return

    if database_url == "sqlite://":
        return

    sqlite_path = database_url.removeprefix("sqlite:///")
    if sqlite_path in {":memory:", ""}:
        return

    Path(sqlite_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=4)
def create_db_engine(database_url: str | None = None) -> Engine:
    """Create and cache a SQLModel engine for the configured workspace graph."""

    resolved_url = database_url or get_database_url()
    ensure_sqlite_directory(resolved_url)
    connect_args = {"check_same_thread": False} if is_sqlite_url(resolved_url) else {}
    echo = os.getenv("COGNIEDA_DB_ECHO", "").strip().lower() == "true"
    engine = create_engine(resolved_url, echo=echo, connect_args=connect_args)
    if is_sqlite_url(resolved_url):
        _enable_sqlite_foreign_keys(engine)
    return engine


def _enable_sqlite_foreign_keys(engine: Engine) -> None:
    """Enable SQLite foreign-key enforcement on each connection."""

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(
        dbapi_connection: Any,
        connection_record: Any,
    ) -> None:
        del connection_record
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_session(database_url: str | None = None) -> Session:
    """Create a database session for the configured workspace graph."""

    return Session(create_db_engine(database_url))


@contextmanager
def session_scope(database_url: str | None = None) -> Iterator[Session]:
    """Provide a small transactional session scope for local operations."""

    session = get_session(database_url)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
