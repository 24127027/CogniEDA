# ADR-006: SQLite as Sole Supported Persistence Boundary

- **Status**: Accepted `[Implemented]`
- **Context**: Supporting multiple database engines before stabilizing scientific transaction semantics leads to dialect fragmentation and unverified DDL triggers.
- **Decision**: SQLite with WAL mode, foreign key enforcement, and immediate transaction locking is the **sole supported persistence boundary** for CogniEDA structural foundation releases.
- **Consequences**: All database models, DDL migrations, and DDL triggers are written and tested exclusively against SQLite. PostgreSQL or distributed database support is out of current scope.
- **Rejected Alternatives**: Multi-dialect ORM abstraction layer without triggers, raw file-system JSON stores.
- **Verification**: `tests/db/test_s3b_sqlite_schema_equivalence.py`.
