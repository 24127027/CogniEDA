# Limitations and bottlenecks

These are verified constraints of the bounded current implementation.
[Current state](current-state.md) owns capability detail.

## Architectural gap

- The active typed research-state foundation is transitional and does not
  implement the minimum complete scientific loop defined by MVP-v2.
- The bounded runtime approves and activates exact Plan/Task bundles and
  enforces dependency eligibility for semantic DATA tool calls. Only `DATA` is
  executable; scientific parent/leaf feasibility and graph work remain absent.
- The current materialized SessionFrame can hold one Objective and one
  DataProfile plus ordered Assumption, Task, Evidence, and Discovery values,
  but is not the canonical reference-based session-membership FCO and does not
  implement Objective-bound multi-session isolation. Retained Discovery
  membership is context membership, not ownership of its complete provenance
  graph.
- A Human-approved different Objective can replace an empty materialized
  Objective scope. If old-Objective Tasks, Evidence, or Discoveries are retained,
  replacement fails closed because canonical successor membership and
  cross-Objective reuse rules are not implemented.
- Direct Task-to-Evidence linkage is a bounded transitional capability. Canonical
  Hypothesis, EvidenceRequest, ExecutionRun, AnalysisFrame, evaluation, and
  admission lineage remain **Deferred** and are required by MVP-v2.

## Implementation gap

- Bounded Planner behavior, append-only native model conversation history, and
  deterministic Data Explorer-to-Evidence admission are **Implemented**
  at bounded library surfaces. The in-process Application retains its current
  successor SessionFrame and model-backed conversation turns, but durable
  restart/recovery and complete-loop composition are **Deferred**.
- Plan V1 domain and side-effect-free candidate validation are
  **Implemented**, and append-only repository plus exact approval/activation
  behavior is **Verified on SQLite**. Durable recovery, successor lineage, and
  non-DATA Task DAG runtime are **Deferred**.
  `ScientificInvestigationRun`, `InvestigationPlan`,
  `InvestigationProtocol`, `EvidenceRequest`, `DataWorkOrder`,
  `EvaluationBundle`, `ScientificInvestigationOutcome`, `DiscoveryProposal`,
  and `GovernanceDecision` have no supported implementation.
- Hypothesis Analyst and Graph Miner remain unregistered scaffolds. Discovery
  and Hypothesis remain canonical FCO names but have no active bounded runtime.
- Plan-owned Objective proposal is **Implemented**. Plan approval may approve a
  new Objective but may reference only exact already-admitted Assumptions;
  Planner-side Assumption assessment/admission is **Deferred**. Planner proposes
  DATA Tasks only as part of the exact review bundle; internal Capability
  dispatch is hidden behind the approved semantic tool. Task persistence
  supports status change only. Active Task
  values are immutable; changing Task meaning requires a new identity, while
  status change produces a replacement with the same identity and instruction.
- Planner's `PlannerDeps` contains the dispatcher and model-hidden application
  execution-session service. `run_data_work` is the only active semantic tool
  and is omitted from `plan_or_answer`. Scientific-investigation and graph-query
  tools are **Deferred** because their executors are not runnable.
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
  REPL and is **Partially implemented**. Its Application owns successor
  materialized SessionFrame state, exact Planner-context materialization, and
  complete native-message model turns only for the
  current process; no durable recovery, supported end-to-end application
  runtime, worker, service API, or product CLI exists.
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
- Planner graph tests use a deterministic fake Agent supplied by a fake
  `AgentFactoryPort`; they prove independent typed result contracts, exact
  `PlannerDeps` injection, minimal lifecycle/epistemic graph state, native-
  message delta propagation, separated conversation, Evidence/Discovery answer
  support, Assumption quarantine without command bypass, and fail-closed
  behavior. Separate execution-session tests use a real temporary CSV, the real
  dispatcher and Data Explorer, SQLite Task transition and Evidence admission,
  and successor-context propagation.
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
- SessionFrame snapshots use an internal serialized SQLite envelope; this is a
  bounded round-trip seam that preserves retained Discovery exactly, not
  M5-A/M5-B durable runtime authority or the future reference-membership
  design.
- The persistence helper is not composed with `Workspace`; without an explicit
  `COGNIEDA_DB_URL`, it retains a provisional package-local SQLite default.
  Binding authoritative persistence under `<workspace>/.cognieda/state/` is
  **Deferred** rather than implied here.
- No non-SQLite database is tested.

## Verification gap

- Full pytest collection includes the rewritten M1-B Planner tests. The three
  former donor import blockers were removed rather than restored as
  compatibility APIs.
- A bounded harness proves real dispatcher-compatible Data Explorer execution,
  application Evidence admission, dynamic Plan eligibility, and successor
  PlannerContext propagation. No supported user dataset-adoption and
  user-to-response test exists; bounded in-process composition does not
  establish MVP-v2.
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
