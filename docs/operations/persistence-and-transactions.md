# Persistence and transactions

CogniEDA's scientific lifecycle transitions are larger than individual table
writes. A physically valid row can still create epistemically contradictory
state when the rest of its required transition is absent. The application
layer therefore owns multi-record transactions, while repositories serve as
bounded persistence adapters.

> **Implementation status:** The listed application transaction owners,
> fail-closed public scientific repository writes, private staging hooks,
> rollback, replay, CAS, and fencing paths are **Implemented** and **Verified on
> SQLite**. Protection against arbitrary direct ORM or SQL access is
> **Partially implemented** and is not a security boundary.

## Four different persistence roles

These roles are related but not interchangeable:

| Role | Owns | Must not be inferred from it |
| --- | --- | --- |
| domain schema | typed domain meaning, validation, and lifecycle vocabulary | physical table layout or commit ownership |
| repository | bounded queries, record mapping, expected-state checks, and transaction-scoped staging | an end-to-end workflow or scientific authority |
| SQLModel model | physical mapping, relationships, indexes, and database constraints | FCO ontology, protected context, or validity policy |
| migration | transformation of an existing physical database and installation of database guards | runtime business logic |

The domain model cannot be reconstructed from tables alone. A migration is not
a normal writer. A repository is not an alternate application service.

## Why the application owns transactions

An application transaction owner can see the complete cross-record invariant.
It opens one unit of work, reconstructs durable authority, stages all required
effects through repositories or guarded SQL, and commits once. Losing a guard
or raising at any stage rolls back the complete write set.

This costs more service code, detached plans, explicit session propagation,
private staging APIs, replay logic, repeated lifecycle validation, and larger
tests. CogniEDA accepts that complexity because:

```text
a scientific lifecycle transition
is larger than a single table write
```

Splitting a write set could leave Evidence without its run transition,
Discovery without completed lifecycle state, or a validity event without all
of its dependent effects.

## Current transaction owners

| Owner | Durable write set it owns | Must not do | Replay, concurrency, and backend qualification |
| --- | --- | --- | --- |
| `ExecutionAttemptTransitionService` | ExecutionRun state, attempt succession, execution outbox/inbox state, claim/lease/fencing transitions, and staged run effects used by larger owners | admit Evidence or Discovery, evaluate a claim, or complete terminal scientific state independently | CAS, lease owner/token, fencing, deterministic replay/conflict checks, and uniqueness are **Verified on SQLite** |
| `execute_evidence_admission_plan` | AnalysisFrame and Evidence insertion, ExecutionRun admission state, exact inbox consumption, and Hypothesis transition to ready-for-evaluation | interpret Evidence, create an EvaluationControl, or create Discovery | deterministic identities, exact replay/conflict classification, guarded run transition, one commit, and rollback are **Verified on SQLite** |
| `EvaluationTransitionService` | EvaluationControl lifecycle, claims, proposal publication, retry, cancellation, invalidation, and conflict state | make a governance decision or mark the control committed | CAS, bundle/proposal fingerprints, unique identity, claim fencing, and replay checks are **Verified on SQLite** |
| `GovernanceAuthorityIssuer` | one principal-bound, purpose-bound, expiring GovernanceAuthority | decide a proposal or mutate scientific lifecycle state | clean unit of work, authority fingerprints, and constraint handling are **Verified on SQLite** |
| `DiscoveryAdmissionGovernanceService` | one exact ProposalDecision and its relationship to durable authority | author or rewrite the scientific proposal, create Discovery, or complete the Hypothesis | exact replay/conflict checks and one governance commit are **Verified on SQLite** |
| `AtomicDiscoveryAdmissionService` | admission claim state, exact Discovery copy, conclusion SessionFrame, Hypothesis evaluation, terminal Task completion, EvaluationControl commitment, and ProposalDecision consumption | reinterpret the proposal or admit a partial lifecycle | claim owner/token/fence, CAS, deterministic identity, exact replay, rollback, and SQLite writer serialization are **Verified on SQLite** |
| `AtomicValidityPropagationService` | source validity transition, all applicable dependent effects, SessionFrame freshness effects, and immutable ValidityEvent insertion | delete history, author replacement scientific claims, or accept caller-selected dependent effects | server-built plan, fingerprints, CAS, exact replay, one commit, and SQLite writer serialization are **Verified on SQLite** |
| `commit_planner_operations` | approved ordinary workflow changes, PlannerOperation commitment, and the approved execution bundle delegated through transition-service staging | directly create Evidence, Discovery, execution protocol rows, conclusion frames, terminal analytical Task completion, or evaluated Hypotheses | all-or-nothing batch commit plus guarded staging are **Verified on SQLite** |

Each owner begins and commits its transaction in the application boundary
identified above. Repositories participate in the same supplied session.
Coordinators may find work and call an owner; planners may propose operations;
runtime facades may delegate calls. None of those roles becomes the transaction
owner merely by initiating the call.

The concrete persistence participants are intentionally mixed:

- `ExecutionAttemptTransitionService` applies guarded SQLModel updates to
  ExecutionRun, outbox, inbox, Hypothesis, and Task records; its staging hooks
  let a larger application owner reuse those transitions without an early
  commit.
- Evidence admission uses `AnalysisFrameRepository` and `EvidenceRepository`
  private staging plus execution-transition staging for run, inbox, and
  Hypothesis effects.
- evaluation uses `EvaluationControlRepository`.
- authority issuance inserts `GovernanceAuthorityRecord` directly in its owned
  session; governance decision recording uses `ProposalDecisionRepository` plus
  authoritative record reads.
- Discovery admission uses `DiscoveryAdmissionClaimRepository` and
  `DiscoveryRepository` private staging plus guarded lifecycle-record updates
  and conclusion-frame construction.
- validity propagation uses `ValidityEventRepository` private staging plus
  guarded updates to the source and every planned dependent record.
- Planner commit uses bounded research repositories where available and
  delegates the execution bundle to
  `ExecutionAttemptTransitionService` staging.

Direct guarded SQLModel updates inside a named application owner are not
repository ownership. They do increase the need for architecture tests that
detect an equivalent update outside the owner.

## Repositories are adapters

Repositories may:

- load and map records;
- apply bounded and validity-aware queries;
- check expected state or uniqueness;
- stage one insert or transition in a caller-owned session; and
- expose private hooks needed to assemble an atomic application write set.

They must not independently complete a scientific lifecycle, consume governance
authority outside its owner, coordinate multiple bounded contexts, or commit a
partial validity cascade.

Public Evidence and Discovery creation fails closed. AnalysisFrame creation for
Evidence admission, EvaluationControl creation, ValidityEvent insertion,
ProposalDecision staging, and Discovery-admission claim transitions use private
transaction-bound hooks. Ordinary workflow repositories still expose legitimate
isolated writes for objects such as Objective, Assumption, Task, Hypothesis, and
non-conclusion SessionFrame, but terminal analytical transitions are sealed and
delegated to their scientific transaction owner.

## Why staging hooks are private

A private hook allows an owner to stage one effect without committing it. If
every scientific `create` or `update` were public, a caller could persist one
valid-looking effect while omitting the rest of its required lifecycle chain.

The underscore is an application boundary, not cryptographic protection.
Python privacy is conventional. Architecture tests detect unsupported writers,
repository guards reject selected public operations, and database constraints
or triggers protect selected physical invariants. Direct access to a session or
database can still bypass some of those layers.

## Alternate-writer classification

The supported source paths divide as follows:

| Class | Meaning | Current findings |
| --- | --- | --- |
| A | canonical transaction owner | the owners in the matrix above |
| B | private transaction-bound adapter | private repository stage hooks used by an A owner |
| C | legitimate isolated workflow write | nonterminal Task/Hypothesis changes, ordinary SessionFrames, Objective/Assumption changes, Planner operations and user workflow decisions |
| D | compatibility or test-only path | model construction in tests and fixtures, targeted migrations, and the legacy payload migrator |
| E | reachable alternate writer | none found on the supported application path |

An E-class writer for Evidence, Discovery, validity provenance, governance
consumption, or terminal scientific lifecycle state would be a source defect,
not a documentation exception.

## Layered enforcement

| Invariant family | Schema validation | Application owner | Repository guard | Database constraint or trigger | Architecture test | Convention |
| --- | --- | --- | --- | --- | --- | --- |
| typed payload shape and lifecycle vocabulary | primary | repeats cross-record checks | maps and validates | selected checks and foreign keys | detects duplicate persisted enums and model definitions | not sufficient alone |
| complete Evidence admission | local shape only | primary atomic write-set owner | public creation fails closed; private staging | uniqueness, relationships, and guarded updates | enforces permitted caller and writer paths | direct database access remains possible |
| exact Discovery admission and terminal cutover | local shape only | primary atomic write-set owner | public creation fails closed; private staging | uniqueness, foreign keys, claim/decision triggers, and guarded updates | enforces sole admission writer | not a malicious-access boundary |
| immutable validity provenance | command/event shape | primary transition owner | event staging is private | validity-event update/delete triggers | enforces sole owner and repository surface | new backends need equivalent guards |
| scientific payload immutability | validates new values | supported services never rewrite the core | public mutation guards cover supported paths | incomplete; no universal payload trigger | detects supported bypasses | direct ORM/SQL discipline remains necessary |
| ordinary workflow lifecycle | typed updates | Planner commit or scoped service | public methods guard sealed terminal states | selected constraints | checks terminal ownership | ordinary nonterminal writes remain intentionally public |

Database triggers help when an ORM path is bypassed, but they cover selected
families rather than every scientific payload. They are not a substitute for
one application transaction owner.

## SQLModel and the `db.models` facade

SQLModel is the current persistence mapping choice because it combines typed
Python records, SQLAlchemy transactions, explicit constraints, and practical
SQLite operation. It does not own ontology, scientific authority, transaction
boundaries, migration history, or active-retrieval policy.

Its costs include duplicate domain and persistence representations, sensitivity
to metadata registration and import order, enum and timestamp identity hazards,
backend-specific JSON and DDL behavior, and the temptation to pass table models
or direct ORM writes across application boundaries.

`db.models` is the only deliberate persistence compatibility facade. Its
explicit `__all__` registers the current table models and the persistence
`TimestampedRecord` and `utc_now` helpers deterministically. It exports no
repositories or application services, uses no wildcard aggregation, and is
tested in fresh processes across import orders. Schema and repository
compatibility aliases remain prohibited.

The facade is classified as a known temporary deviation. Its risks include
becoming a dumping ground, hiding bounded ownership behind stale aliases,
registering duplicate models, and encouraging application code to treat
physical model location as domain ownership.

Within persistence models, `src/db/models/common.py` owns the canonical
timezone-aware UTC helper and timestamp base. Persisted lifecycle enums come
from `src/schemas/enums.py`; duplicate enum identities are prohibited.
Schema-layer defaults may use their own schema helper because that is a
different layer, but persistence model modules must not fork their common
identity.

## Backend and security qualification

All concurrency, trigger, migration, and transaction behavior described here
is **Verified on SQLite** only. Repository abstraction does not prove backend
portability. Direct database credentials also sit below these application
boundaries; the design protects supported internal code paths, not hostile or
arbitrary database access.

## Revisit triggers

Revisit packaging and ownership when:

- another database backend is supported;
- multiple concurrent writers or large effect sets change lock behavior;
- bounded contexts become separately deployed services;
- a transaction span would cross databases or external participants; or
- an event-driven cutover replaces a local atomic transaction.

The mechanism may change, but a redesign must preserve one inspectable owner for
each scientific transition, fail-closed partial writes, exact authority and
replay identity, and no physically valid but epistemically contradictory state.

## Related canonical concepts

- [Planner operations and approvals](planner-and-approvals.md)
- [Operation approval workflows](operation-approval-workflows.md)
- [SQLite and portability](sqlite-and-portability.md)
- [SQLite initialization and migrations](sqlite-and-migrations.md)
- [Atomic persistence workflow](atomic-persistence-workflow.md)
- [Scientific authority](../concepts/scientific-lifecycle/scientific-authority.md)
- [Atomic validity propagation](../concepts/validity/validity-propagation.md)

## Implementation orientation

Application owners are under `src/application/`; repository adapters are under
`src/repositories/`; physical models and initialization are under `src/db/`.
Writer ownership and package boundaries are enforced by focused checks under
`tests/architecture/`.
