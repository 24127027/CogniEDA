from __future__ import annotations

from pathlib import Path

import pytest

from cognieda.infrastructure.persistence.init_db import init_db
from cognieda.infrastructure.persistence.session import create_db_engine, get_session


def pytest_addoption(parser):
    parser.addoption(
        "--dataset", action="store", default=None, help="Path to a dataset for integration tests"
    )


@pytest.fixture
def db_session(tmp_path: Path):
    database_url = f"sqlite:///{(tmp_path / 'test_artifacts.sqlite3').as_posix()}"
    create_db_engine.cache_clear()
    init_db(database_url)
    session = get_session(database_url)
    try:
        yield session
    finally:
        session.close()
        create_db_engine.cache_clear()
