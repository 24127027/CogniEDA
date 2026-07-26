# Implementation gap analysis

> **Implementation status:** **Partially implemented**.
>
> This page is a source-oriented current-versus-target reference. It is not the
> canonical introduction to CogniEDA, and source code remains authoritative for
> what currently exists.

Canonical reader-facing maturity and comparison now belong to
[CogniEDA current state](../current-state.md) and the
[capability and maturity map](../capability-and-maturity-map.md). Future
sequencing and exit criteria belong to the [roadmap](../roadmap.md).

Reader-facing ownership for the operational gaps belongs to
[Planner boundary and operation model](../planner-boundary-and-operation-model.md),
[Retrieval strategy and scaling](../retrieval-strategy-and-scaling.md),
[SessionFrame scaling and resume boundary](../session-frame-scaling-and-resume-boundary.md),
and [Product surface and bootstrap boundary](../product-surface-and-bootstrap-boundary.md).

## Current implementation versus target

| Area | Target design | Current implementation | Status and principal gap |
| --- | --- | --- | --- |
| FCO ontology | Exactly Objective, DataProfile, Assumption, Task, Hypothesis, Evidence, Discovery, and SessionFrame | Pydantic schemas, persistence models, and repositories use this set | **Implemented**; there is no production graph abstraction |
| Runtime composition | One explicit, fail-closed composition boundary independent of deployment topology | `CogniEDARuntime` and an external factory loader assemble injected dependencies in process and initialize persistence | **Implemented**; a production deployment factory, product process, and automatic recovery loop are **Unsupported** |
| Persistence ownership | One application owner per load-bearing multi-record transition; repositories remain adapters | Scientific cutovers have explicit application owners, private staging hooks, public writer seals, and architecture checks | **Implemented** and **Verified on SQLite**; direct ORM/SQL access is a convention and database-credential boundary rather than absolute enforcement |
| Database evolution | Immutable, ordered, fail-closed upgrades across supported historical states | Startup applies a fixed sequence of targeted SQLite upgrades and legacy quarantine | **Partially implemented**; current behavior is **Verified on SQLite**, but no immutable revision registry, general downgrade, or online migration exists |
| Planner governance | Understand intent, stage governed operations, coordinate specialists, and commit approved changes | Task, decomposition, Objective, durable approval, session-bound resume, and fresh execution proposal paths exist; nodes construct sessions and repository records directly | **Partially implemented**; no scientific-writer bypass was found, while direct persistence composition and incomplete answer/suggestion/review/pause/closure paths are **Known deviation** or **Unsupported** |
| Hypothesis Analyst | Operationalize a Task and evaluate Evidence without raw-data access | Protected evaluation consumes a closed repository-built bundle and returns a typed proposal or failure; the Planner still authors the operational contract | **Partially implemented**; evaluation exists, operationalization ownership is a **Known deviation** |
| Data Explorer | Execute an approved contract and return observation-only output | Typed result, registry, dispatcher, and per-runtime factory boundaries exist | **Partially implemented**; a concrete production adapter is **Unsupported** |
| Graph Miner | Typed graph retrieval, lineage, staleness, conflict, and coverage analysis | A stub wrapper and bounded SQL-backed Discovery retrieval exist | **Deferred** as a coherent workflow |
| PydanticAI boundary | Canonical model construction, dependencies, typed output, validation, and retry | Used by selected Planner and protected evaluation adapters; deployment must provide suitable model configuration | **Partially implemented** |
| LangGraph boundary | Deterministic routing, interruption, checkpointing, and workflow state | Planner topology uses LangGraph with process-local `MemorySaver`; durable PlannerOperation and ExecutionApproval records support only bounded identity-based resume | **Partially implemented**; arbitrary graph progress and product conversation resume are **Unsupported** |
| Task/Hypothesis/Discovery lineage | Eligible terminal Task to one Hypothesis to one Discovery | Repository and database guards enforce at-most-one cardinality; parent Tasks cannot produce Discoveries | **Implemented** |
| Proposal approval | An exact durable proposal and authorized decision precede governed mutation or execution | Task, decomposition, Objective, execution, and Discovery paths bind exact proposals or contracts | **Partially implemented**; authorization is not uniform across every Planner operation |
| Atomic scientific mutation | Ordered scientific changes persist all-or-nothing | Evidence admission, Discovery admission, validity propagation, and relevant workflow transitions have application-owned transactions | **Implemented** and **Verified on SQLite** |
| Execution attempts | Durable outbox/inbox, fencing, idempotency, cancellation, and retry | Transition, recovery, and race-handling services exist | **Partially implemented**; production worker bootstrap is **Unsupported** |
| Evidence admission | Deterministic AnalysisFrame and immutable Evidence materialization from observation-only output | The in-process finalizer admits provenance and Evidence, advances the run and Hypothesis, and consumes the inbox atomically without creating Discovery | **Implemented** and **Verified on SQLite** |
| Context type safety | Assumptions only in planning; protected Discovery synthesis uses scientific inputs only | Evaluation uses an immutable repository-authoritative bundle with a closed provenance manifest | **Implemented** for protected evaluation; broader generated-view and Graph Miner context is **Deferred** |
| Discovery governance | Exact proposal plus independent authority precede atomic admission | An injected principal resolver, expiring authority grant, durable decision, and separate exact-copy admission path exist | **Implemented** and **Verified on SQLite**; production authentication is **Unsupported** |
| Validity propagation | One authorized event updates every applicable dependent atomically | Typed validity commands propagate across supported DataProfile, AnalysisFrame, Evidence, and ExecutionRun sources through a CAS-guarded atomic transaction | **Implemented** and **Verified on SQLite**; a general production validity-authority issuer is **Unsupported** and validity has no separate claim/lease/fencing protocol |
| SessionFrame | User-governed current context with auditable inclusion | Append-only snapshots, database-global latest/latest-active lookup, bounded projections, conclusion frames, and validity supersession exist | **Partially implemented**; no user/session/Objective-scoped selector, branch head, complete resume, or item-governance UX; pin-only freshness and Objective-management latest selection are **Known deviation** |
| Provenance | Reproducible data view, method, code, environment, seed, and artifacts | AnalysisFrame, ExecutionRun, and Evidence capture the minimum implemented chain | **Partially implemented**; the general reproducibility envelope is a **Design target** |
| Dataset versioning and cleaning | Approved physical transformations create new versions and DataProfiles | CSV/Parquet profiling and a DVC interface exist | **Partially implemented**; executable DVC and governed cleaning are **Deferred** |
| Retrieval | Governed graph traversal with validity, scope, lineage, and relevance | Bounded repository retrieval applies explicit and lifecycle exclusion before deterministic lexical scoring; commit revalidates exact active profile, while wrong-profile context can consume budget and Objective, SessionFrame-identity, and operation-scope filters are absent | **Partially implemented**; Graph Miner, semantic indexing, and typed operation-scope admission are **Deferred** |
| Evidence cache | Validity-keyed reuse that can never author Discovery | No durable cache service exists | **Deferred** |
| Product surface | Supported authenticated entry point and restart-safe coordination | A fail-closed in-process composition root and external runtime-factory seam require deployment-supplied identity, Analyst, and Data Explorer adapters; tracked agent capability configuration references undefined MCP servers and skill directories without tracked definitions | **Unsupported**; no CLI, API, worker, daemon, Python bootstrap, or runnable default capability configuration |
| Quality gates | Reproducible tests, lint, formatting, typing, startup, migrations, and CI | Local commands and extensive tests exist | **Partially implemented**; tracked CI and strict typing remain absent or incomplete |

## Protected invariants already present

- DataProfile and Evidence scientific payloads are frozen and append-oriented.
- Only an active terminal analytical Task with an accepted DataProfile can
  admit a Hypothesis.
- One Task admits at most one Hypothesis, and one Hypothesis admits at most one
  Discovery.
- Parent Tasks produce neither Hypotheses nor Discoveries.
- Evidence admission is observation-only, fenced, and atomic; failure produces
  no Evidence or Discovery.
- Protected Discovery synthesis excludes Assumptions, Tasks, existing
  Discoveries, raw chat history, and unverified generated views.
- Governance authorizes the exact persisted proposal; the scientific
  specialist cannot approve or persist its own result.
- Discovery admission requires active same-Hypothesis Evidence and copies the
  authorized proposal exactly.
- Validity propagation preserves historical records while removing invalid
  state from active retrieval.

The owning sources are the schema, model, repository, application, Planner,
executor, and memory packages identified in the
[module responsibilities](module-responsibilities.md) reference.

## Highest-risk gaps

1. Proposal authorization is not uniform across every Planner mutation.
2. The Planner still authors the analytical contract, and no concrete
   production Data Explorer exists.
3. The composition root requires trusted principal, model, and executor
   adapters, but no supported deployment supplies them.
4. Validity and scientific-transaction guarantees are verified only on SQLite.
5. SessionFrame governance, project resume, and user-facing invalidation
   recovery are incomplete; a pin-only affected Discovery reference may leave
   frame status active even though repository-current retrieval remains safe.
6. Execution approval can remain durably approved after a later admission
   failure without a complete retry path, and existing-Hypothesis reuse fails
   closed at the correct lifecycle owner.
7. Product identity, concrete analytical adapters, and restart coordination are
   absent even though an in-process runtime and factory seam exist.
8. Provenance is not yet sufficient for broad reproducibility claims.
9. Strict static typing and tracked CI remain repository-level quality debt.
10. Changed-contract successor creation is outside the current retry path.
11. Direct ORM or SQL access can bypass invariants that are enforced only by
   application services, repository guards, or architecture tests.
12. The targeted migration sequence lacks mechanically immutable revision
    identities even though historical behavior must remain append-only.
13. The tracked agent capability configuration is not self-consistent:
    `config/agents.toml` references MCP servers whose definitions are commented
    out, and configured skill directories contain no tracked skill definitions.
    Model-backed Planner adapters therefore require corrected deployment
    configuration before they are runnable.

## Target dependency order

This is design sequencing, not implementation history:

1. preserve the existing responsibility, authority, and type-safety contracts;
2. put remaining Planner mutations behind uniform proposal and authorization
   boundaries;
3. move analytical-contract operationalization to the intended specialist
   boundary;
4. provide a concrete observation-only Data Explorer and governed dataset
   version workflow;
5. expose the existing Evidence, evaluation, governance, Discovery, and
   validity services through an authenticated product boundary;
6. complete SessionFrame governance, resume, and generated-view behavior;
7. add Graph Miner retrieval and then validity-keyed Evidence caching;
8. broaden reproducibility, portability, observability, and release gates.

## Owner decisions still required

- relational graph abstraction versus another graph store;
- Hypothesis approval and changed-contract successor semantics;
- the minimum reproducibility envelope for Evidence admission;
- governance policy for plans, Assumptions, cleaning, conflicts, and
  SessionFrame changes;
- SessionFrame current-cardinality, scoping, and legacy migration policy;
- supported product surface and deployment topology;
- backend portability, concurrency, and migration-tooling policy;
- release-gate policy for lint, formatting, typing, and CI.
