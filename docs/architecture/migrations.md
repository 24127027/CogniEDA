# Database Migrations & Schema Evolution

> **Status**: `[Implemented]` / `[Verified on SQLite]`

CogniEDA uses an idempotent, targeted database migration framework designed for workspace-local SQLite databases.

---

## 1. Migration Entry Point & Functions

Migration functions are located in `src/db/migrations.py`:
- `init_db(database_url)` (`src/db/init_db.py`): Initializes a fresh database and applies all schema DDL and trigger definitions.
- `upgrade_database(engine)` (`src/db/migrations.py`): Runs targeted idempotent upgrade functions in strict sequential order.

Targeted Upgrade Chain:
1. `upgrade_pre_repair_database(engine)`: Fenced execution run columns and indexes.
2. `upgrade_objective_lifecycle_schema(engine)`: Objective revisions table and active objective constraint.
3. `upgrade_task_motivation_schema(engine)`: Task discovery motivation links.
4. `upgrade_task_review_schema(engine)`: Planning review reason fields.
5. `upgrade_evaluation_control_schema(engine)`: Evaluation control digest and status columns.
6. `upgrade_proposal_decision_schema(engine)`: Governance authority tables and immutability triggers.
7. `upgrade_validity_events_schema(engine)`: Validity metadata and quarantine tables.
8. `upgrade_discovery_admission_claim_schema(engine)`: Fenced discovery admission claim triggers.
9. `upgrade_legacy_payloads_schema(engine)`: Legacy payload migration helper.

---

## 2. Trigger Guards & Immutability Enforcement

SQLite triggers enforce strict immutability at the database level:
- `governance_authorities_immutable_core`: Prevents modification of core authority fields.
- `proposal_decisions_immutable_core`: Prevents modification of decision fields.
- `proposal_decisions_monotonic_consumption`: Enforces one-way consumption (`consumed 0 -> 1`).
- `validity_events_immutable` / `validity_events_no_delete`: Prevents updates or deletions of validity events.
- `discovery_admission_claims_immutable_identity`: Prevents claim identity mutation.
- `discovery_admission_claims_terminal`: Prevents state updates once a claim reaches a terminal state (`COMMITTED`, `CONFLICT`, `CANCELLED`, `INVALIDATED`).
- `proposal_decisions_exact_consumption`: Rejects consumption unless backed by an exact committed discovery admission claim chain.

---

## 3. Historical Migration Assets Policy

Existing migration functions and historical schema repairs in `src/db/migrations.py` are **immutable historical assets**. They must not be reorganized or refactored in documentation or exit packages.
