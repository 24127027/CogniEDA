# Implementation gap analysis

> **Implementation status:** **Partially implemented**.
>
> This page is a source-oriented current-versus-target reference. It is not the
> canonical introduction to CogniEDA, and source code remains authoritative for
> what currently exists.

## Current implementation versus target

| Area | Target design | Current implementation | Status and principal gap |
| --- | --- | --- | --- |
| FCO ontology | Exactly Objective, DataProfile, Assumption, Task, Hypothesis, Evidence, Discovery, and SessionFrame | Pydantic schemas, persistence models, and repositories use this set | **Implemented**; there is no production graph abstraction |
| Planner governance | Understand intent, stage governed operations, coordinate specialists, and commit approved changes | Narrow Task, decomposition, Objective, and execution proposal paths exist; several nodes know sessions and repository records | **Partially implemented**; direct persistence knowledge is a **Known deviation** |
| Hypothesis Analyst | Operationalize a Task and evaluate Evidence without raw-data access | Protected evaluation consumes a closed repository-built bundle and returns a typed proposal or failure; the Planner still authors the operational contract | **Partially implemented**; evaluation exists, operationalization ownership is a **Known deviation** |
| Data Explorer | Execute an approved contract and return observation-only output | Typed result, registry, dispatcher, and per-runtime factory boundaries exist | **Partially implemented**; a concrete production adapter is **Unsupported** |
| Graph Miner | Typed graph retrieval, lineage, staleness, conflict, and coverage analysis | A stub wrapper and bounded SQL-backed Discovery retrieval exist | **Deferred** as a coherent workflow |
| PydanticAI boundary | Canonical model construction, dependencies, typed output, validation, and retry | Used by selected Planner and protected evaluation adapters; deployment must provide suitable model configuration | **Partially implemented** |
| LangGraph boundary | Deterministic routing, interruption, checkpointing, and workflow state | Planner topology uses LangGraph; specialist evaluation is deliberately outside it | **Partially implemented**; checkpoint/resume product behavior is incomplete |
| Task/Hypothesis/Discovery lineage | Eligible terminal Task to one Hypothesis to one Discovery | Repository and database guards enforce at-most-one cardinality; parent Tasks cannot produce Discoveries | **Implemented** |
| Proposal approval | An exact durable proposal and authorized decision precede governed mutation or execution | Task, decomposition, Objective, execution, and Discovery paths bind exact proposals or contracts | **Partially implemented**; authorization is not uniform across every Planner operation |
| Atomic scientific mutation | Ordered scientific changes persist all-or-nothing | Evidence admission, Discovery admission, validity propagation, and relevant workflow transitions have application-owned transactions | **Implemented** and **Verified on SQLite** |
| Execution attempts | Durable outbox/inbox, fencing, idempotency, cancellation, and retry | Transition, recovery, and race-handling services exist | **Partially implemented**; production worker bootstrap is **Unsupported** |
| Evidence admission | Deterministic AnalysisFrame and immutable Evidence materialization from observation-only output | The in-process finalizer admits provenance and Evidence, advances the run and Hypothesis, and consumes the inbox atomically without creating Discovery | **Implemented** and **Verified on SQLite** |
| Context type safety | Assumptions only in planning; protected Discovery synthesis uses scientific inputs only | Evaluation uses an immutable repository-authoritative bundle with a closed provenance manifest | **Implemented** for protected evaluation; broader generated-view and Graph Miner context is **Deferred** |
| Discovery governance | Exact proposal plus independent authority precede atomic admission | An injected principal resolver, expiring authority grant, durable decision, and separate exact-copy admission path exist | **Implemented** and **Verified on SQLite**; production authentication is **Unsupported** |
| Validity propagation | One authorized event updates every applicable dependent atomically | Typed validity events propagate across DataProfile, AnalysisFrame, Evidence, and ExecutionRun state through a fenced transaction | **Implemented** and **Verified on SQLite**; production authority workflow is **Unsupported** |
| SessionFrame | User-governed current context with auditable inclusion | Append-only snapshots, latest-active lookup, bounded projections, conclusion frames, and validity supersession exist | **Partially implemented**; complete resume and item-governance UX is **Unsupported** |
| Provenance | Reproducible data view, method, code, environment, seed, and artifacts | AnalysisFrame, ExecutionRun, and Evidence capture the minimum implemented chain | **Partially implemented**; the general reproducibility envelope is a **Design target** |
| Dataset versioning and cleaning | Approved physical transformations create new versions and DataProfiles | CSV/Parquet profiling and a DVC interface exist | **Partially implemented**; executable DVC and governed cleaning are **Deferred** |
| Retrieval | Governed graph traversal with validity, scope, lineage, and relevance | Bounded repository retrieval excludes explicit and invalid lifecycle state before deterministic lexical scoring; profile mismatches remain warned context-only candidates, while Objective and operation-scope filters are absent | **Partially implemented**; stricter profile/scope admission, graph traversal, and persistent semantic indexing are **Deferred** |
| Evidence cache | Validity-keyed reuse that can never author Discovery | No durable cache service exists | **Deferred** |
| Product surface | Supported authenticated CLI, API, or worker loop | A fail-closed in-process composition root requires external adapters | **Unsupported** |
| Quality gates | Reproducible tests, lint, formatting, typing, startup, migrations, and CI | Local commands and extensive tests exist | **Partially implemented**; tracked CI and strict typing remain absent or incomplete |

## Protected invariants already present

- DataProfile and Evidence scientific payloads are frozen and append-oriented.
- Only an active terminal analytical Task with an accepted DataProfile can
  admit a Hypothesis.
- One Task admits at most one Hypothesis, and one Hypothesis admits at most one
  Discovery.
- Parent Tasks do not produce Discoveries.
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
   recovery are incomplete.
6. Provenance is not yet sufficient for broad reproducibility claims.
7. Strict static typing and tracked CI remain repository-level quality debt.
8. Changed-contract successor creation is outside the current retry path.

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
- release-gate policy for lint, formatting, typing, and CI.
