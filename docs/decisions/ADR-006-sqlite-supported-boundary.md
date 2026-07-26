# ADR-006: SQLite as the supported persistence boundary

**Decision classification:** Current-stage implementation choice with durable
transaction-safety obligations.

**Implementation status:** **Verified on SQLite**. Other database backends and
distributed transaction topologies are **Unsupported**.

## Context

CogniEDA persists workflow, scientific provenance, governance, admission,
validity, and active-context state. Several supported transitions update
multiple records and rely on compare-and-set predicates, uniqueness, claims,
fencing, triggers, rollback, and exact replay.

The current runtime is an in-process, local-first composition boundary without
a production CLI, service, or distributed worker topology. A supported database
claim must match the concrete locking, initialization, migration, and race
behavior that source and tests actually exercise.

## Problem

“Uses SQLAlchemy repositories” is not a database-portability guarantee.
Isolation, writer concurrency, uniqueness-conflict timing, trigger semantics,
JSON and timestamp representation, migration DDL, and retry behavior vary by
backend.

The project needs a clear supported boundary on which atomic scientific
transitions can be stated honestly, while leaving room for a future backend
decision.

## Failure mode

If SQLite-verified behavior is described as database-independent, a deployment
could move to another backend while retaining implicit assumptions about
first-write serialization, lock order, trigger coverage, or conflict timing.
Discovery admission or validity propagation could then commit against stale
authority, miss a newly created dependent, deadlock without a retry policy, or
accept a partial chain as replay success.

The inverse failure is also harmful: treating SQLite as merely a disposable
test database would hide the fact that it is the current operational
persistence boundary and that its mechanisms are load-bearing today.

## Tempting alternatives

- claim portability because repositories abstract queries;
- accept any SQLAlchemy database URL and defer concurrency testing;
- choose PostgreSQL before a service and worker topology exists;
- use filesystem JSON or chat history as the authority store;
- move every invariant into SQLite triggers;
- remove database-specific qualification from canonical documentation; or
- present SQLite as the permanent deployment architecture.

## Decision

SQLite is the sole supported persistence backend for the current runtime.
Current transaction, concurrency, initialization, migration, trigger, rollback,
replay, and recovery guarantees are qualified to SQLite.

The engine enables foreign keys, configures a bounded busy timeout, and uses
WAL mode for file-backed databases. Application transaction owners combine
SQLite's writer behavior with explicit CAS predicates, uniqueness, claims and
fencing where applicable, deterministic identities, and full rollback.

SQLite is a current-stage implementation choice, not a foundational epistemic
invariant. The invariant is that each supported scientific and governance
transition has one authoritative owner, atomic complete effects, safe replay,
and explicit failure semantics on the supported backend.

Repository abstraction does not confer backend support. A new backend requires
a separate decision and owner-by-owner verification.

## Invariant protected

No supported database claim may be broader than its verified locking,
constraint, migration, and failure behavior. Scientific state must not become
physically valid but epistemically contradictory because backend semantics were
assumed rather than proved.

## Current implementation

`CogniEDARuntime` invokes canonical database initialization when it is
constructed. The session layer configures SQLite connections. Targeted in-code
upgrades, metadata creation, trigger installation, and legacy quarantine prepare
fresh and supported existing databases.

Focused tests exercise:

- transaction commit and rollback;
- foreign keys, uniqueness, and guarded updates;
- exact replay and same-key conflict;
- execution, evaluation, and admission claims and fencing;
- selected concurrent writers and winner verification;
- current trigger families;
- fresh and upgraded schema behavior; and
- interrupted legacy migration rollback and retry.

Some owners materially depend on SQLite writer serialization. Discovery
admission performs guarded writes before reconstructing the final authoritative
bundle under the writer lock. Validity propagation discovers and CAS-updates a
deterministic dependent set without a separate validity claim, lease, or
fencing protocol.

## Tradeoffs

The decision provides a reproducible one-file workspace database, low
operational overhead, practical crash/replay tests, and a concrete transaction
boundary before deployment topology is chosen.

It also imposes:

- limited concurrent-writer capacity;
- backend-specific trigger and migration code;
- local-file operational constraints;
- re-verification cost for every future backend;
- no distributed transaction or network-partition semantics;
- lock timing that differs from row-locking databases; and
- a risk that contributors mistake ORM portability for behavioral portability.

## Known limitations

The repository does not support PostgreSQL, MySQL, distributed transactions,
multiple-host writer guarantees, external transaction participants, online
migration, zero-downtime migration, or a general production database service.

Current triggers protect selected governance, validity-event, admission-claim,
and legacy-quarantine concerns. They do not universally enforce immutable
scientific payloads. Direct ORM or SQL access can bypass some
application/repository rules and is not treated as a hostile-access security
boundary.

The targeted migration chain is non-Alembic and has no general downgrade or
immutable revision registry.

## Risks

- SQLite writer serialization can become a throughput bottleneck.
- In-memory and file-backed database behavior can diverge in concurrency tests.
- Trigger behavior may be hidden from ordinary ORM review.
- A new direct writer can bypass guards that exist only in application or
  repository code.
- Historical migration functions can be edited without a revision system
  mechanically detecting the change.
- A future backend port can preserve method signatures while changing isolation
  and conflict behavior.

## Revisit triggers

Revisit this decision when:

- a production CLI, API, daemon, or worker topology requires remote
  persistence;
- multiple concurrent or multiple-host writers are a normal workload;
- cross-workspace queries or a managed database service are required;
- transaction effect sets make local writer-lock duration unacceptable;
- customer-managed databases introduce multiple released schema histories;
- online or zero-downtime migration becomes necessary; or
- PostgreSQL or another backend is proposed for support.

The replacement decision must preserve exact scientific authority, complete
atomic write sets, deterministic replay and conflict semantics, historical
retention, fail-closed migration, and testable recovery.

## Consequences for future work

A backend port must define isolation and explicit locking for every transaction
owner, deterministic lock ordering and retries, replacements for load-bearing
triggers, equivalent constraint timing, exact type round trips, and migration
from supported historical states.

It must rerun concurrent exact and conflicting replay, crash-stage rollback,
claim/lease/fencing, stale-source, newly-created-dependent, and schema
equivalence scenarios on the new backend. Repository interfaces can be reused
only after those semantics are proved.

Operational documentation must continue to say **Verified on SQLite** until a
new backend has its own supported initialization, migration, and transaction
evidence.

## Related canonical concepts

- [SQLite boundary and portability](../sqlite-boundary-and-portability.md)
- [Persistence and transaction ownership](../persistence-and-transaction-ownership.md)
- [Database initialization and migrations](../database-initialization-and-migrations.md)
- [From runtime composition to atomic persistence](../from-runtime-composition-to-atomic-persistence.md)
- [Governance and Discovery admission](../governance-and-discovery-admission.md)
- [Atomic validity propagation](../atomic-validity-propagation.md)

## Implementation orientation

SQLite connection behavior is defined in `src/db/session.py`; initialization is
in `src/db/init_db.py`; targeted upgrades and legacy quarantine are in
`src/db/migrations.py` and `src/db/legacy_migration.py`. Application transaction
owners are under `src/application/`. Focused backend behavior is exercised under
`tests/db/`, with writer-ownership checks under `tests/architecture/`.
