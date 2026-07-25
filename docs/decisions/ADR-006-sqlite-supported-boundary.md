# ADR-006: SQLite as Sole Supported Persistence Boundary

**Status:** Accepted; implemented and verified for SQLite only.

## Context

Scientific transaction semantics depend on concrete lock, trigger, and migration
behavior. Multi-dialect claims without equivalent tests would be unsafe.

## Decision

SQLite is the sole supported persistence runtime for the current foundation.
Initialization enables foreign keys and applies ordered, targeted in-code schema
repairs, table creation, triggers, and legacy quarantine.

## Consequences

PostgreSQL and distributed-database behavior is not claimed. There is no Alembic
or general downgrade framework.

## Rejected alternatives

An unverified multi-dialect abstraction and filesystem JSON as the authority
store.

## Enforcement

`tests/db/test_s3b_sqlite_schema_equivalence.py` verifies the explicit 21-table
facade and SQLite schema/trigger equivalence. Migration tests under `tests/db`
exercise upgrades and trigger guards.
