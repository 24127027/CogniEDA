# Capability and maturity map

> **Implementation status:** CogniEDA is **Partially implemented** overall. This
> page summarizes source-backed capability boundaries; it is not a product
> feature list or a test report.

This page is the reader-facing companion to
[CogniEDA current state](current-state.md). Each row distinguishes a usable
in-process boundary from the complete workflow or product surface that would
make it operational for users. Future dependencies and exit criteria belong to
the [roadmap](roadmap.md).

## How to read the map

The status vocabulary is exact:

- **Implemented** means supported behavior exists on the current in-process
  library path.
- **Verified on SQLite** qualifies tested persistence, transaction, migration,
  race, or concurrency behavior; it is not a separate product capability.
- **Partially implemented** means a coherent subset exists but the workflow or
  user boundary is incomplete.
- **Design target** means the intended boundary is documented without a
  complete supported implementation.
- **Deferred** means the project intentionally postpones the work.
- **Known deviation** means source differs from the preferred design within an
  explicit temporary boundary.
- **Unsupported** means no supported product or runtime capability exists.

A schema, interface, configuration key, directory, or test fixture alone does
not establish an implemented capability.

## Research state and workflow

| Capability group | Purpose | Current status | Implemented boundary | Important limitations | Next required boundary |
| --- | --- | --- | --- | --- | --- |
| eight-object ontology | keep scientific knowledge, workflow, provenance, and context roles distinct | **Implemented** | exactly eight FCO schemas, models, and repositories; non-FCO roles stay separate | direct ORM or SQL access is not an absolute enforcement boundary | retain the ontology while adding product adapters and views |
| Objective lifecycle | preserve governed research intent and revision provenance | **Partially implemented** | create/update operations, one active Objective, append-only revisions, successor frame helper | no complete natural-language/user lifecycle; frame succession uses global latest | trusted interaction plus scoped Objective and SessionFrame selection |
| Assumption lifecycle | make planning premises explicit without laundering them into conclusions | **Partially implemented** | schemas, repository transitions, Planner operation commit, planning-context inclusion | natural-language creation, testability review, replacement, and conflict UX are incomplete | user-governed Assumption workflow that preserves synthesis exclusion |
| Task workflow | turn research intent into governed analytical work | **Partially implemented** | Task creation/update, hierarchy, motivation, decomposition, approval, and repository-current commit | answer, review, cleaning, and closure branches remain absent | complete supported Planner interaction without alternate writers |
| Hypothesis eligibility and cardinality | bind one eligible terminal analytical Task to at most one test contract | **Implemented** | active/terminal/profile/parent guards and at-most-one persistence constraint | Planner still authors operationalization; existing-Hypothesis reuse fails closed | Analyst-owned operationalization and an explicit reuse or successor policy |

## Execution, Evidence, and scientific interpretation

| Capability group | Purpose | Current status | Implemented boundary | Important limitations | Next required boundary |
| --- | --- | --- | --- | --- | --- |
| execution approval and attempts | make execution explicit, durable, replay-aware, and cancellable | **Partially implemented** | exact contract approval, durable run/outbox/inbox, attempt identity, retry, cancellation, lease, fence, dispatch, receipt, and reconciliation; persistence behavior is **Verified on SQLite** | no worker loop; a later admission failure can strand an `APPROVED` approval | restart-safe coordination and explicit terminal recovery |
| Data Explorer protocol | isolate observation from scientific interpretation | **Partially implemented** | typed observation result, single-registration registry, dispatcher, and per-runtime factory | no concrete production adapter, real dataset method registry, or artifact policy | one observation-only Data Explorer over a supported dataset path |
| Evidence admission | materialize exact execution provenance and immutable observations | **Implemented** | deterministic AnalysisFrame/Evidence identities, exact contract binding, atomic admission, replay/conflict handling, and technical-failure isolation; **Verified on SQLite** | broad code/environment/seed reproducibility remains incomplete | preserve the sole writer while adding real adapter provenance |
| protected evaluation | author scientific wording from an authority-safe bundle | **Partially implemented** | repository-built closed bundle, explicit exclusions, no-tool Analyst, typed proposal/failure, durable evaluation control, replay and fencing | deployment must inject a real model provider; no production evaluation loop | production Analyst adapter and restart coordination |
| governance | bind a real decision to an exact scientific proposal | **Partially implemented** | principal contract, scoped expiring authority, exact proposal decision, replay/conflict, rejection, cancellation, and consumption; **Verified on SQLite** | no production principal resolver or external approval surface | trusted local identity and user-facing decision interaction |
| Discovery admission | materialize only an authorized evidence-bound claim | **Implemented** | sole materializer, exact proposal-copy, claim/lease/fence, atomic full write set, rollback/replay/conflict, and conclusion SessionFrame; **Verified on SQLite** | no correction or successor-claim product workflow | surface results and later correction without mutating prior claims |

## Validity, active context, and retrieval

| Capability group | Purpose | Current status | Implemented boundary | Important limitations | Next required boundary |
| --- | --- | --- | --- | --- | --- |
| validity propagation | retain history while removing invalid state from current authority | **Implemented** | typed commands, fingerprints, deterministic plans, immutable events, dependent propagation, replay/conflict, and active exclusion; **Verified on SQLite** | no direct Discovery-source command, successor claim, notification, or review queue | product authority and user-visible invalidation recovery |
| SessionFrame continuity | persist bounded current context without making it scientific authority | **Partially implemented** | append-oriented snapshots, planning/answer projections, pins, exclusions, reasons, conclusion frames, and validity supersession | pin-only freshness, global selection, active predecessors, and no branch/user/session UI | scoped selection, succession policy, and restart-safe governance |
| bounded retrieval | choose current context after type and lifecycle admission | **Partially implemented** | structural candidates, validity/type filtering, deterministic lexical scoring, context-only motivations, and bounded results | wrong-profile budget use; unused Objective/SessionFrame bindings; no operation scope | typed scoping, budget partitioning, and measured retrieval quality |
| semantic retrieval and Graph Miner | improve recall and traverse governed lineage at scale | **Deferred** | semantic scorer protocol and Graph Miner placeholder do not form a supported capability | default scoring is lexical; Graph Miner raises or remains unregistered; no persistent index | define authority-first semantic/hybrid retrieval after the product slice |

## Planner, runtime, and persistence

| Capability group | Purpose | Current status | Implemented boundary | Important limitations | Next required boundary |
| --- | --- | --- | --- | --- | --- |
| Planner coordination | stage governed operations and route supported research workflows | **Partially implemented** | explicit commands, selected model-backed drafts, Task/decomposition/Objective/execution paths, durable approvals, bounded resume, and commit delegation | TODO/pass branches, stale route labels, direct persistence composition, process-local graph checkpoints | complete only the interactions needed by the first product slice; extract a facade where recovery or scoping requires it |
| runtime composition | expose one fail-closed authority graph to a host process | **Implemented** | explicit `CogniEDARuntime` dependency injection and external factory loader | no deployment factory, host lifecycle, health policy, or adapter selection | explicit deployment contract supplied by the first product slice |
| SQLite persistence | preserve current research state and atomic application-owned transitions | **Implemented** | initialization, session setup, targeted upgrades, selected guards, legacy quarantine, and canonical transactions; load-bearing behavior is **Verified on SQLite** | no immutable revision registry, universal payload triggers, cross-backend parity, or multi-process guarantee | restart-safe local coordination first; portability only at explicit triggers |
| dataset versioning and cleaning | ensure transformed data creates new governed state | **Partially implemented** | CSV/Parquet loading and profiling plus a DVC interface boundary | DVC adapter and governed cleaning are not executable product workflows | approved transformations that create new dataset versions and DataProfiles |

## Product, operations, and capability configuration

| Capability group | Purpose | Current status | Implemented boundary | Important limitations | Next required boundary |
| --- | --- | --- | --- | --- | --- |
| supported product host | let a user run one persistent governed investigation | **Unsupported** | no product host exists; only direct library/runtime invocation is supported | no CLI, API, worker, daemon, workspace opener, user interaction, output delivery, or supervisor | Package 7A through 7D in dependency order |
| production identity and Analyst adapter | resolve a trusted principal and execute protected evaluation | **Unsupported** | protocols and injected seams exist | no deployment implementation or provider policy | trusted local adapters with fail-closed startup |
| concrete Data Explorer | execute a real analytical method against supported data | **Unsupported** | protocol, registry, and dispatcher exist | no registered production implementation | observation-only adapter with typed provenance and failure behavior |
| tools, skills, and MCP configuration | compose model-backed worker capabilities coherently | **Known deviation** | loaders validate workers, built-ins, skills, and MCP references and fail explicitly | checked-in MCP references are undefined; configured skill directories have no tracked definitions; built-in graph/data tools are placeholders | Package 7A deployment configuration; Package 7B analytical tools |
| operational recovery and observability | make coordination dependable across restart | **Unsupported** | individual reconciliation and recovery functions exist | no durable polling loop, supervisor, logs/health contract, or product recovery policy | restart-safe in-process coordination |

## Product consequence summary

The infrastructure is not nonfunctional merely because product adapters are
absent. Its guarded library paths can create and preserve scientifically typed
state. The missing layer changes who can use it and under what operational
conditions:

- without identity, exact-governance contracts cannot bind a deployment user;
- without a concrete Data Explorer, execution cannot produce real supported
  observations;
- without restart-safe coordination, durable records do not guarantee complete
  workflow progress after a process loss;
- without scoped SessionFrame selection, multiple investigations cannot choose
  current context reliably;
- without a product host, users cannot drive the governance model end to end.

## Roadmap ownership

The first product-integration boundary is divided into four dependent
milestones:

1. Package 7A — trusted local identity and Analyst adapters;
2. Package 7B — Concrete Data Explorer;
3. Package 7C — restart-safe in-process coordination;
4. Package 7D — persistent end-to-end product slice.

These milestones are **Design target**. Their blockers, invariants, non-goals,
and observable exit criteria are canonical in the [roadmap](roadmap.md).

## Implementation orientation

The main source areas are:

- research state: `src/schemas/research/`, `src/repositories/research/`, and
  `src/db/models/research.py`
- Planner and ordinary mutation: `src/agents/planner/` and
  `src/application/orchestrator/`
- execution and specialist boundaries: `src/application/execution/` and
  `src/agents/executor/`
- scientific admission: `src/application/evidence/`,
  `src/application/evaluation/`, `src/application/governance/`, and
  `src/application/discovery/`
- validity and active context: `src/application/validity/` and `src/memory/`
- composition and persistence: `src/application/runtime.py`,
  `src/application/runtime_loader.py`, and `src/db/`
- configuration: `config/`, `skills/`, and `src/tools/`

Technical references remain available through the
[documentation index](index.md). Source and focused tests remain authoritative
when a summary and implementation differ.
