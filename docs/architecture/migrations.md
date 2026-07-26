# Migrations and schema evolution

> **Role:** Technical reference. **Canonical concept owner:**
> [SQLite initialization and migrations](../operations/sqlite-and-migrations.md).
> **Contributor entry:** [Contributor documentation](../development/index.md).
> **Current-state owner:** [CogniEDA current state](../current-state.md).

> **Implementation status:** current upgrade chain **Implemented** and
> **Verified on SQLite**.

The reader-facing initialization, history, and quarantine rationale is owned by
[SQLite initialization and migrations](../operations/sqlite-and-migrations.md).
This page retains the exact contributor-oriented call order.

## Initialization order

`src/db/init_db.py:init_db` is the checked-in entry point. It creates an engine and calls:

1. `upgrade_pre_repair_database`;
2. `upgrade_objective_lifecycle_schema`;
3. `upgrade_task_motivation_schema`;
4. `upgrade_task_review_schema`;
5. `upgrade_evaluation_control_schema`;
6. `upgrade_proposal_decision_schema`;
7. `upgrade_validity_events_schema`;
8. `SQLModel.metadata.create_all`;
9. `upgrade_discovery_admission_claim_schema`;
10. `upgrade_legacy_payloads_schema`.

There is no generic `upgrade_database` function. Discovery-chain triggers are installed after all
referenced tables exist. The legacy payload step invokes the deterministic
`LegacyPayloadMigrator` and installs its marker/quarantine assets.

## Trigger families

Fresh SQLite initialization installs guards for:

- governance authority immutable core;
- proposal decision immutable core;
- proposal decision monotonic consumption;
- validity event immutable update and no-delete;
- Discovery admission claim immutable identity and terminal-state guard;
- exact proposal-decision consumption;
- legacy quarantine immutable update and no-delete.

Exact names and DDL are source-level details enforced by the focused SQLite
schema-equivalence and legacy-migration tests.

## Guarantees and limits

Focused tests cover fresh initialization, targeted legacy upgrades, idempotent rerun, deterministic
quarantine, interrupted migration rollback/retry, model import order, and SQLite trigger behavior.
One historical task-motivation downgrade helper exists; the project does not claim a general
rollback framework.

**Known deviation:** These are targeted in-code SQLite upgrade assets, not
Alembic revisions. Historical migration behavior is an immutable record of an
already-released transformation: new changes require a new append-only upgrade
step rather than reordering or rewriting old behavior. The current function
chain has no general revision registry that mechanically enforces that rule.
No non-SQLite guarantee is claimed.
