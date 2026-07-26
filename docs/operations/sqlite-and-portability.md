# SQLite and portability

SQLite is CogniEDA's current supported persistence backend. That is a deliberate
current-stage choice for a local-first research-state system, not a claim that
SQLite is universally sufficient or that repository abstraction makes the code
database-independent.

> **Implementation status:** Current initialization, transaction, rollback,
> constraint, trigger, replay, migration, and selected race behavior are
> **Verified on SQLite**. PostgreSQL, MySQL, cross-database parity, distributed
> transactions, multiple-host writers, network-partition behavior, and external
> transaction participants are **Unsupported**.

## Why SQLite is supported now

The current repository is an in-process runtime without a production service
topology. SQLite provides:

- one file-backed database for a local workspace;
- low deployment and recovery overhead;
- explicit SQLAlchemy transaction boundaries;
- reproducible fresh and legacy database fixtures;
- practical crash, rollback, replay, and race testing; and
- sufficient concurrency for the currently verified single-database profile.

This lets the project prove scientific cutovers before committing to a network
database and worker topology. SQLite is a current-stage implementation choice;
atomic scientific lifecycle transitions are the durable operational boundary.

## What is actually verified

Focused source paths and tests cover:

- all-or-nothing local transactions and rollback;
- foreign-key and uniqueness enforcement;
- compare-and-set updates and affected-row verification;
- execution and admission claims, leases, and fencing where those protocols
  exist;
- exact replay versus same-key conflict;
- selected competing-worker and validity/admission races;
- trigger-enforced immutability and lifecycle constraints for the trigger
  families that exist;
- fresh initialization and targeted existing-database upgrades; and
- rollback-safe legacy quarantine.

The verified statement is always about the specific application owner,
database mechanism, and test scope. It is not a proof about another driver,
isolation level, or deployment.

## SQLite-specific mechanisms

The file-backed engine enables foreign keys, configures a bounded busy timeout,
and uses WAL journal mode. SQLite serializes writers once a write transaction
begins. Some scientific owners deliberately perform a guarded write before
reconstructing their final authoritative bundle so the remaining cutover is
protected by the acquired SQLite writer lock.

Other SQLite-specific mechanisms include:

- partial indexes and uniqueness-conflict timing;
- SQLite trigger syntax and trigger error behavior;
- inspection of `sqlite_master` in schema-equivalence tests;
- file-backed versus in-memory connection behavior;
- JSON, timestamp, UUID, and enum representation through the current dialect;
- engine disposal between selected process or race tests; and
- lock/busy timing during concurrent replay or competing claims.

The architecture separates invariant from mechanism:

| Architectural invariant | Current SQLite mechanism |
| --- | --- |
| Discovery admission is atomic | one local transaction, guarded lifecycle updates, claim fencing, uniqueness, and writer serialization |
| validity propagation is complete or absent | one local transaction, server-built effect plan, CAS on every effect, event uniqueness, and writer serialization |
| one execution attempt transition wins | CAS, claim owner/token, lease/fencing predicates, and uniqueness |
| committed governance provenance cannot be silently rewritten | application ownership plus selected SQLite triggers |
| uncertain outcomes are safely repeatable | deterministic identities, exact replay verification, uniqueness, and rollback |

A future backend may replace every mechanism in the right column. It must
preserve the invariants in the left column.

## Portability risk by transaction owner

| Owner | Risk | What another backend must reverify |
| --- | --- | --- |
| `ExecutionAttemptTransitionService` | Moderate | CAS row counts, lease/fencing races, predecessor and outbox uniqueness, retry policy, and conflict timing |
| `execute_evidence_admission_plan` | High | lock acquisition order, competing admission, deterministic winner reload, multi-row rollback, and inbox consumption |
| `EvaluationTransitionService` | Moderate | partial uniqueness, claim CAS, stale bundle/proposal conflicts, retry, and isolation behavior |
| `GovernanceAuthorityIssuer` | Low | timestamp/expiry representation, constraint handling, and transaction failure behavior |
| `DiscoveryAdmissionGovernanceService` | Moderate | decision uniqueness, exact replay conflict timing, and replacement for SQLite trigger guards |
| `AtomicDiscoveryAdmissionService` | High | explicit row/advisory locking, lock order, claim fencing, first-write serialization assumptions, and exact replay under concurrent workers |
| `AtomicValidityPropagationService` | High | protection against newly appearing dependents, source and target locking, phantom behavior, lock order, conflict retries, and event/effect replay |
| `commit_planner_operations` | Moderate | batch isolation, active-objective uniqueness, execution-bundle CAS, deadlock order, and transaction retry policy |

“Low” does not mean portable today. Every row remains unverified outside
SQLite. Repository interfaces do not remove isolation, locking, trigger,
serialization, or representation differences.

## Why the highest-risk owners are high risk

Discovery admission explicitly relies on a guarded early write holding the
SQLite writer lock while authoritative state is reconstructed and the complete
cutover is staged. PostgreSQL would require an explicit locking and ordering
design rather than an assumption that equivalent serialization happens.

Validity propagation discovers a dependent set, then applies a multi-record
plan. Under a backend with concurrent row-level writers, it must prevent a new
dependent or a conflicting transition from appearing between discovery and
commit. CAS on the rows already found is necessary but may not by itself guard
against phantoms.

## Triggers are bounded protection

Current trigger families protect selected governance-authority and decision
fields, committed decision consumption, ValidityEvent immutability,
Discovery-admission claim identity and terminal transitions, and legacy
quarantine immutability.

They do not provide universal immutable-payload protection for every FCO or
provenance record. They are SQLite-specific, can hide behavior from an ORM
reader, and add migration and portability cost. Application-owned transactions
and repository guards remain necessary.

## What is not proved

The current suite does not prove:

- PostgreSQL or MySQL isolation semantics;
- behavior with multiple host processes writing over a network;
- safe distributed leases or clocks;
- transaction coordination with object stores, queues, or external services;
- recovery across network partitions;
- online or zero-downtime migration;
- cross-workspace database operation; or
- automatic retries for every backend-specific transient failure.

These capabilities are **Unsupported**, not implicit future commitments.

## Requirements before another backend is supported

A backend decision must provide and test:

1. an explicit isolation and locking model for each transaction owner;
2. deterministic lock ordering and deadlock/retry behavior;
3. equivalent uniqueness and constraint timing;
4. replacements for every load-bearing trigger;
5. exact JSON, timestamp, UUID, and enum round trips;
6. fresh initialization and upgrades from supported historical states;
7. concurrent exact replay and conflicting replay;
8. crash and rollback behavior at every transaction stage;
9. stale-source and newly-created-dependent handling; and
10. documented operational limits for writer count and deployment topology.

Backend selection is a **Deferred** portability decision. A repository-only port
is insufficient.

## Revisit triggers

Revisit SQLite when:

- a remote database service is required;
- multiple concurrent writers become a normal workload;
- cross-workspace queries are required;
- transaction effect sets exceed practical local locking time;
- workers run across hosts;
- customer-managed databases become supported; or
- availability requirements cannot tolerate a local file boundary.

The invariant to preserve is not “use SQLite.” It is that every scientific and
governance transition has exact authority, complete atomic effects, safe replay,
and explicit failure semantics on the supported backend.

## Related canonical concepts

- [Persistence and transactions](persistence-and-transactions.md)
- [SQLite initialization and migrations](sqlite-and-migrations.md)
- [Discovery governance and admission](../concepts/scientific-lifecycle/discovery-governance-and-admission.md)
- [Atomic validity propagation](../concepts/validity/validity-propagation.md)
- [SQLite as the verified database](../design-decisions/sqlite-as-the-verified-database.md)

## Implementation orientation

Connection behavior is defined in `src/db/session.py`; initialization is in
`src/db/init_db.py`; targeted upgrades and trigger installation are in
`src/db/migrations.py` and `src/db/legacy_migration.py`. Transaction owners are
under `src/application/`. Focused database behavior is exercised under
`tests/db/`, with transaction ownership checks under `tests/architecture/`.
