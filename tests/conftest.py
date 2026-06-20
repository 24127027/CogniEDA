from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db.init_db import init_db  # noqa: E402
from db.session import create_db_engine, get_session  # noqa: E402


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
