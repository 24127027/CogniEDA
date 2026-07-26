# SQLite initialization and migrations

Runtime construction opens the configured persistence boundary and invokes one
canonical initialization sequence. That sequence serves both a fresh SQLite
database and an existing supported SQLite database, but the work performed in
those two cases is different.

> **Implementation status:** Ordered targeted upgrades, SQLModel metadata
> creation, trigger installation, legacy quarantine, and idempotent restart
> behavior are **Implemented** and **Verified on SQLite**. A general revision
> registry, Alembic infrastructure, complete downgrade support, online
> migration, zero-downtime deployment, and non-SQLite migration path are
> **Unsupported**. Mechanical enforcement of immutable migration history is a
> **Known deviation**.

## The canonical initialization entry point

`init_db()` creates the configured engine and applies this conceptual order:

1. repair pre-current execution and protocol structures;
2. upgrade Objective lifecycle and revision constraints;
3. upgrade Task motivation and review fields;
4. upgrade protected-evaluation control state;
5. upgrade governance authority and proposal-decision state;
6. upgrade validity-event structures;
7. register and create missing current SQLModel tables;
8. upgrade Discovery-admission claims after their referenced tables exist; and
9. run the legacy scientific-payload migration and quarantine pass.

The exact functions and DDL are implementation details. The ordering is
load-bearing: earlier repairs make old structures safe, metadata creation fills
missing current tables, claim guards wait for referenced tables, and legacy
payload handling runs only after the current authority structures exist.

All current targeted upgrade functions reject non-SQLite dialects. Although the
engine helper can construct another SQLAlchemy URL, the supported
initialization boundary cannot.

## Fresh database initialization

For a fresh database:

- importing the explicit `db.models` facade registers the physical models in
  `SQLModel.metadata`;
- targeted upgrade steps safely find no legacy structure or create prerequisite
  protocol structures where required;
- `SQLModel.metadata.create_all()` creates missing current tables;
- later upgrade steps install claim indexes and trigger guards that depend on
  the complete schema; and
- the legacy migrator creates its marker and quarantine structures and records
  a completed pass.

Fresh initialization is tested for model-registration determinism and physical
schema equivalence. Canonical documentation deliberately does not freeze
checkout-specific object counts.

## Existing database upgrade

For an existing supported database, the same entry point:

- inspects known legacy table and column shapes;
- adds compatible fields, indexes, and relationships;
- repairs or abandons unsafe in-flight execution state;
- rejects contradictory Objective revision or active-state data;
- quarantines partial evaluation, governance, validity, or admission identity
  rather than granting it current authority;
- installs current trigger guards idempotently; and
- migrates or quarantines legacy scientific payloads inside one rollback-safe
  transaction.

Unsupported or ambiguous state fails closed. An old record can be preserved
without being treated as scientifically legitimate.

## Current migration model

The migration system is a fixed, in-code sequence of targeted SQLite upgrade
functions applied at initialization. It is:

- startup-applied by `init_db()`;
- ordered explicitly in Python;
- shape-aware for known legacy databases;
- idempotent for supported starting states;
- paired with explicit legacy quarantine;
- non-Alembic; and
- without a general downgrade framework.

One targeted downgrade helper exists for a historical Task field. That isolated
helper does not make arbitrary downgrade or rollback-to-revision behavior a
supported capability.

The current mechanism is a known temporary deviation from a revisioned migration
system suited to many released database generations. It is adequate for the
currently verified SQLite boundary, but its history is not protected by an
immutable revision registry.

## Historical migrations are immutable records

The governing rule is:

```text
A historical migration is an immutable record
of a previously released transformation.
```

Editing an already-applied transformation makes two databases with the same
apparent version carry different histories. Reordering old steps can also make
a fresh database and an upgraded database converge accidentally in tests while
real deployed databases retain incompatible state.

New schema behavior therefore requires a new append-only upgrade step. Existing
released behavior must not be rewritten merely to make the current schema look
cleaner.

This rule has costs:

- compatibility code and old assumptions remain visible;
- the sequence grows over time;
- multiple historical starting states need tests;
- cleanup cannot erase transformations already applied elsewhere; and
- future revision tooling must adopt the existing history without silently
  renumbering it.

## Migration immutability classification

The review classification is `C. partial`:

- initialization order is explicit and tested;
- known upgrade paths are idempotent and focused fixtures compare fresh and
  upgraded schema behavior;
- migration and trigger creation remain inside the canonical initialization
  boundary; and
- legacy migration has a durable marker.

However, the broader targeted function chain has no general immutable revision
identity, append-only registry, or automated check that a previously released
function body was not edited. The documentation rule is stronger than its
mechanical enforcement. This is a residual operational risk, not evidence of a
current supported-database contradiction.

## Legacy quarantine

The legacy payload migrator runs its scientific-state transformation in one
transaction. It creates immutable quarantine records and a migration marker,
then classifies old state conservatively:

- exact observation chains can become current AnalysisFrame and Evidence
  provenance;
- partial or authority-free execution state is abandoned or quarantined;
- unverified Discoveries are invalidated or quarantined rather than admitted;
- legacy terminal Hypotheses and Tasks are retained but adjusted according to
  verifiable Evidence/admission state; and
- unverified conclusion frames are superseded or quarantined.

Quarantine insertion and migration markers are idempotent. An interrupted
migration rolls back and can be retried. The scope is a known set of legacy
shapes, not a universal import tool.

The principle is:

```text
data preservation != automatic scientific legitimacy
```

Ambiguous lineage, missing provenance, duplicate claims, partial old
transactions, or unknown authority cannot be repaired by optimistic inference.

## Trigger installation and limits

Initialization installs trigger families for selected concerns:

- immutable committed validity-event provenance;
- immutable governance and proposal-decision core fields plus monotonic
  decision consumption;
- Discovery-admission claim identity and terminal-state constraints; and
- immutable legacy quarantine.

These guards protect selected invariants even if a normal ORM path is bypassed.
They are not universal scientific-payload immutability, do not replace
application transaction ownership, and require backend-specific redesign for
portability.

## Idempotency and fail-closed behavior

Each targeted upgrade inspects the current shape before acting. Existing
compatible objects are retained; missing compatible structures are added;
known incomplete legacy identities are quarantined or moved to conflict state.
Contradictory states that cannot be interpreted safely raise instead of
silently manufacturing authority.

Idempotency means a completed compatible initialization can be run again
without duplicating its effects. It does not mean every arbitrary database
shape is accepted.

## Revisit triggers

Adopt a stronger migration mechanism when:

- multiple released schema generations must be supported;
- customer or externally managed databases exist;
- a general downgrade requirement appears;
- online or zero-downtime migration is required;
- PostgreSQL or another backend becomes supported; or
- deployments cannot run startup migrations under one controlled owner.

Any replacement must preserve ordered upgrade semantics, immutable history,
fresh-versus-upgraded equivalence, fail-closed ambiguity handling, quarantine
provenance, and transaction rollback.

## Related canonical concepts

- [SQLite and portability](sqlite-and-portability.md)
- [Persistence and transactions](persistence-and-transactions.md)
- [Atomic persistence workflow](atomic-persistence-workflow.md)
- [Validity over time](../concepts/validity/validity-over-time.md)

## Implementation orientation

The entry point is `src/db/init_db.py`. Engine configuration is in
`src/db/session.py`. Targeted upgrades are in `src/db/migrations.py`; scientific
legacy classification and quarantine are in `src/db/legacy_migration.py`.
Model-registration, schema-equivalence, initialization, and legacy behavior are
tested under `tests/db/`.
