# Limitations and bottlenecks

These are verified constraints of the bounded MVP implementation, not a sprint
backlog. [Current state](current-state.md) owns capability detail.

## Architectural gap

- M1-A implements the approved executable subset, not the full canonical Task,
  plan-version, scientific, governance, validity, or continuity architecture.
- Active MVP Task has no PlanRevision membership, dependencies, assignment,
  ordering, approval, parent/leaf semantics, or canonical Task kind. Those
  contracts are **Deferred** to M1-C rather than represented by legacy fields.
- The MVP SessionFrame supports one active Objective and one active
  DataProfile but does not implement Workspace-wide multi-Objective isolation.
- Direct Task-to-Evidence linkage is executable MVP state. Canonical
  Hypothesis, EvidenceRequest, ExecutionRun, AnalysisFrame, evaluation, and
  admission lineage remain **Deferred** to M2/M3-B.

## Implementation gap

- M1-B Planner behavior and M3-A deterministic Data Explorer-to-Evidence
  admission are **Implemented** at bounded library surfaces. M5-A retained
  single-session composition is **Deferred**.
- `PlanRevision`, `ScientificInvestigationRun`, `InvestigationPlan`,
  `InvestigationProtocol`, `EvidenceRequest`, `DataWorkOrder`,
  `EvaluationBundle`, `ScientificInvestigationOutcome`, `DiscoveryProposal`,
  and `GovernanceDecision` have no supported implementation.
- Hypothesis Analyst and Graph Miner remain unregistered scaffolds. Discovery
  and Hypothesis remain canonical FCO names but have no active MVP runtime.
- Planner successor-state Objective replacement and Assumption addition are
  **Implemented**. Durable Objective and Assumption persistence updates remain
  **Deferred**. Task persistence supports status change only. Active Task
  values are immutable; changing Task meaning requires a new identity, while
  status change produces a replacement with the same identity and instruction.
- Application-authority Evidence admission is **Implemented** for the direct
  M3-A Task-to-Evidence contract and **Verified on SQLite**. It is not the
  canonical scientific M3-B admission contract and does not fabricate
  EvidenceRequest, ExecutionRun, AnalysisFrame, or Hypothesis lineage.
- An admitted DataProfile does not currently retain its physical dataset path
  or a content digest. M3-A verifies the execution request path against Data
  Explorer provenance and verifies reprofiling metrics against the persisted
  profile, but durable dataset-version identity remains a **Known limitation**.
- Non-finite source numbers are excluded from continuous descriptive
  calculations, and non-finite computed statistics become `None`. This is a
  **Known limitation** of bounded profiling, not data-quality governance or
  canonical preprocessing lineage.

## Donor isolation limitation

- Canonical-heavy donor tests for scientific attempts and Discovery retrieval
  are explicitly skipped after the hard cutover. They remain design/test
  material and are not compatibility authority for active schemas.
- The obsolete SessionFrame/context builder was removed; the active M1-A
  SessionFrame schema is the only executable owner. The unregistered
  Hypothesis Analyst, Planner operation contracts, deferred retrieval engine,
  and scientific repositories still contain deferred field references. They
  are not composed into the active M1-A path.
- Fresh SQLite metadata reflects M1-A mappings. Upgrading an existing donor
  database to the hard-cutover schema is **Unsupported**; no production data
  migration is included in this milestone.

## Operational limitation

- Bootstrap composes the in-process S0 dispatcher and bounded Data Explorer.
  The installable `cognieda [PATH]` command reaches the development Planner
  REPL and is **Partially implemented**; no supported end-to-end application
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
- M1-B Planner tests use deterministic fake model and dispatcher boundaries;
  they prove typed capability selection, tracked Task lifecycle, outcome
  consumption, and fail-closed behavior without claiming model-selected real
  Data Explorer filesystem execution.
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
  bounded round-trip seam, not M5-A/M5-B durable runtime authority.
- The persistence helper is not composed with `Workspace`; without an explicit
  `COGNIEDA_DB_URL`, it retains a provisional package-local SQLite default.
  Binding authoritative persistence under `<workspace>/.cognieda/state/` is
  **Deferred** to the runtime/persistence phase rather than implied here.
- No non-SQLite database is tested.

## Verification gap

- Full pytest collection includes the rewritten M1-B Planner tests. The three
  former donor import blockers were removed rather than restored as
  compatibility APIs.
- A bounded harness proves real dispatcher-compatible Data Explorer execution
  and application Evidence admission. No composed user-to-Planner-to-real-Data
  Explorer-to-Evidence-to-SessionFrame-to-response test exists; M3-A library
  completion does not establish M5-A or MVP-I.
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
  not redefine the canonical target or executable MVP subset.
