# Limitations and bottlenecks

These are verified constraints of the bounded current implementation.
[Current state](current-state.md) owns capability detail.

## Architectural gap

- The active typed research-state foundation is transitional and does not
  implement the minimum complete scientific loop defined by MVP-v2.
- Active bounded Task has no Plan-driven dependency eligibility or parent/leaf
  execution semantics. Immutable Plan candidates contain full exact Task
  definitions, exact Objective and admitted Assumption basis, and grouped
  structural dependencies. An independent application service can atomically
  persist an exact authorized bundle and select a Plan active by Objective, but
  only `DATA` is separately executable and no Plan drives execution.
- The current materialized SessionFrame can hold one Objective and one
  DataProfile but is not the canonical reference-based session-membership FCO
  and does not implement canonical Objective-bound multi-session identity. Its
  append-only SQLite envelope is isolated by exact workspace scope. It now
  retains materialized Hypothesis and Discovery research-state membership for
  Planner readability, but it does not retain Tasks as research knowledge and
  does not implement validity-aware selection or the semantic graph.
- Direct Task-to-Evidence linkage is a bounded transitional capability. Canonical
  Hypothesis, EvidenceRequest, ExecutionRun, AnalysisFrame, evaluation, and
  admission lineage remain **Deferred** and are required by MVP-v2.

## Implementation gap

- The Planner cognitive core, in-process LangGraph lifecycle, and deterministic
  Data Explorer-to-Evidence admission are **Implemented** at bounded library
  surfaces. Application owns the stable session identity and `ConversationHistory`
  composed of `ConversationTurn`s and prunable `ConversationSegment`s.
  Planner performs one `plan_or_answer` invocation per graph turn
  with `PlannerToolDeps` and no execution dispatch. Graph state owns the exact
  transient self-contained Plan candidate and completed turn segment; `PlannerContext`
  and native model history are transported fresh via `PlannerRunContext`.
  Candidate retain/replace/discard, natural-language Human review, typed authorization,
  and interrupt/resume are implemented in process. Restart recovery, durable graph
  checkpoints, durable chat-session reopening, and complete-loop composition are **Deferred**.
- The Phase 1 Plan domain and side-effect-free candidate validation are
  **Implemented**, and append-only repository behavior is **Verified on
  SQLite** with exact Objective and Assumption snapshots plus full Task
  reconstruction. Planner can author a transient structurally validated
  candidate. Commit-boundary validation and persistence plus
  objective-scoped active selection are **Verified on SQLite** through an
  application service invoked only by a typed authorization result. Task DAG
  runtime is **Deferred**.
  `ScientificInvestigationRun`, `InvestigationPlan`,
  `InvestigationProtocol`, `EvidenceRequest`, `DataWorkOrder`,
  `EvaluationBundle`, `ScientificInvestigationOutcome`, `DiscoveryProposal`,
  and `GovernanceDecision` have no supported implementation.
- Hypothesis Analyst and Graph Miner remain unregistered scaffolds. Discovery
  and Hypothesis remain canonical FCO names but have no active bounded creation
  or scientific-investigation runtime. Materialized Hypotheses may be retained
  in SessionFrame and read by Planner without granting Planner authoring
  authority.
- Planner may propose a new Objective only inside a transient candidate Plan.
  It cannot create or mutate Assumptions; a candidate may retain only exact
  already-admitted Assumptions. LangGraph retains that exact candidate across
  Human turns and may call the independent admission service after typed
  authorization. The service atomically admits the exact self-contained Plan,
  its Objective, and its Tasks. Task persistence supports status change only. Active Task
  values are immutable; changing Task meaning requires a new identity, while
  status change produces a replacement with the same identity and instruction.
- Application-authority Evidence admission is **Implemented** for the direct
  bounded Task-to-Evidence contract and **Verified on SQLite**. It is not the
  canonical scientific admission contract and does not fabricate
  EvidenceRequest, ExecutionRun, AnalysisFrame, or Hypothesis lineage.
- The bounded admission path atomically persists an initial DataProfile with an immutable
  one-to-one non-FCO `DataProfileDatasetBinding` containing the normalized
  physical dataset reference and `sha256:<64 lowercase hexadecimal characters>`
  digest of the exact loaded file bytes. Evidence admission requires the request
  path and independently observed execution path and digest to match that
  authoritative binding. Admission does not activate or switch the profile.
- This bounded path-plus-content identity is not a complete dataset-versioning
  subsystem. Dataset relocation and successor transformation lineage remain
  **Deferred**; identical bytes at another path require a new explicit profile
  admission, and executable DVC identity resolution is **Unsupported**.
- Non-finite source numbers are excluded from continuous descriptive
  calculations, and non-finite computed statistics become `None`. This is a
  **Known limitation** of bounded profiling, not data-quality governance or
  canonical preprocessing lineage.

## Donor isolation limitation

- The superseded generic retrieval package, retrieval-only schemas and enum,
  and donor policy tests are deleted. Supplemental retrieval remains
  **Deferred**; no embeddings, semantic ranking, or SessionFrame pruning path
  replaces it.
- The bounded materialized SessionFrame is the only executable frame. The
  unregistered Hypothesis Analyst, Planner operation contracts, and scientific
  repositories still contain deferred field references. They are not composed
  into the active bounded path.
- Fresh SQLite metadata reflects the bounded mappings. Upgrading an existing donor
  database to the hard-cutover schema is **Unsupported**; no production data
  migration is included in this milestone.

## Operational limitation

- Bootstrap composes the in-process S0 dispatcher and bounded Data Explorer.
  The installable `cognieda [PATH]` command reaches the development Planner
  REPL and is **Partially implemented**. Bootstrap gives the workspace-scoped
  authoritative SessionFrame repository to the fresh-context provider, not to
  Application, and invokes one fully composed Planner. Planner owns its
  LangGraph, process-local checkpointer/thread and required trusted typed
  serializer, active native-message history, exact candidate state, and Human
  interrupt/resume. A provider exact-materializes
  active-Plan `PlannerContext` fresh for every cognitive invocation. No durable
  graph recovery, durable `ConversationHistory`, unified `SessionMemory`, or
  supported end-to-end application runtime, worker, service API, or product CLI
  exists. No retained runtime writer for current SessionFrame snapshots is
  composed.
- Application-to-CLI presentation uses an in-process EventBus. Normal Planner
  responses, transient Plan proposals, Human clarification requests, and
  command messages are published to renderer subscribers; submit calls do not
  return rendered assistant Messages. Runtime events are not persisted, do not
  own candidates, and have no research-state or admission authority.
- The local Data Explorer path executes only finite validated deterministic
  operations from an explicit absolute CSV or Parquet path. General-purpose
  Python, generated code, `exec`, `eval`, fuzzy column resolution, implicit
  repository data, and environment dataset fallback are **Unsupported**.
- Value counts and group summaries are limited to 50 results, correlation and
  selected-column operations accept at most 10 columns, and Evidence-producing
  profile observations accept at most 50 columns. This bounded result surface
  is a **Known limitation** that prevents accidental dataset dumps.
- Profiling describes the active dataset without duplicate removal, null-row
  removal, or input mutation. Actual cleaning and transformation remain
  blocked until successor dataset and DataProfile semantics exist.
- `DATA_TRANSFORMATION` remains blocked until immutable successor dataset state
  and successor DataProfile handling exist.
- Planner tests use deterministic fake and PydanticAI `FunctionModel`
  boundaries. They prove direct Agent ownership, one invocation per graph turn,
  exact typed dependency injection, active graph-thread native dialogue continuity,
  fresh current-run PlannerContext, candidate retain/replace/discard and exact
  admission, interrupt/resume, thread isolation, controlled failure retention,
  and active-Plan continuation without any executor call.
- Workspace path selection and initialization are **Implemented**, but
  automatic dataset discovery or admission is **Unsupported**. The
  conventional `data/` directory does not itself establish a DataProfile.

## Database limitation

- Current bounded persistence is **Verified on SQLite** only.
- M3-A prevents exact replay duplicates with deterministic Evidence identity
  and rejects conflicting reuse of a Data Explorer work reference. Durable
  inboxes, leases, fencing, and general cross-process replay remain **Deferred**
  to M5-B.
- Durable restart/resume, replay, claims, leases, result inbox, and multi-store
  migration are outside M1-A.
- SessionFrame snapshots use a workspace-scoped internal serialized SQLite
  envelope. Latest committed state in that exact scope is authoritative for the
  current materialized frame and restart-readable, but this is not the
  canonical reference-based M5-A/M5-B session model or durable Planner graph state.
- Bootstrap binds SessionFrame scope to the normalized Workspace root, but
  without an explicit `COGNIEDA_DB_URL` persistence still uses a provisional
  package-local SQLite database.
  Binding authoritative persistence under `<workspace>/.cognieda/state/` is
  **Deferred** rather than implied here.
- No non-SQLite database is tested.

## Verification gap

- The configured full pytest gate stops during collection because the inherited
  `tests/runtime/test_bootstrap_config.py` imports absent
  `resolve_model_config`. The same failure reproduces at exact clean parent
  `acdf229a50ff6292bd0914a6a64e8d5b2c7d6c50`.
- Configured Ruff and strict mypy also retain exact-parent debt: 15 Ruff findings
  and 80 mypy errors in 15 files. The Planner lifecycle changed boundary passes
  both checks.
- A bounded harness proves real dispatcher-compatible Data Explorer execution
  and application Evidence admission. No composed user-to-Planner-to-real-Data
  Explorer-to-Evidence-to-SessionFrame-to-response test exists; bounded
  library completion does not establish MVP-v2.
- No production performance envelope, non-SQLite validation, or external
  integration test exists. The first-party documentation regression is
  intentionally limited to internal Markdown links, relative anchors, and
  compatibility-only redirect language.

## Unsupported feature

- DVC execution, graph-database integration, external MCP services, service
  APIs, UI, and the product CLI are **Unsupported**.
- Cross-Objective Evidence reuse and cross-Objective relation admission have
  no supported path and must remain fail closed.
- General-purpose Python execution and analytical operations outside the
  finite M3-A set are **Unsupported**. Streaming, multi-session coordination,
  and successor transformation remain **Deferred**.

## Documentation limitation

- Current status is a dated source/test audit and can drift when runtime code
  changes. Capability changes must update this status track in the same change.
- Source-layout documentation describes implementation ownership only and does
  not redefine the canonical target or MVP-v2.
