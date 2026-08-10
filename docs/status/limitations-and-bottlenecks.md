# Limitations and bottlenecks

These are verified constraints of the bounded MVP implementation, not a sprint
backlog. [Current state](current-state.md) owns capability detail.

## Architectural gap

- M1-A implements the approved executable subset, not the full canonical Task,
  plan-version, scientific, governance, validity, or continuity architecture.
- Active MVP Task has no PlanRevision membership, dependencies, assignment,
  ordering, approval, parent/leaf semantics, or canonical Task kind. Those
  contracts are **Deferred** to M1-C rather than represented by legacy fields.
- The MVP SessionFrame retains cumulative Objective and DataProfile histories
  with one active selector for each, but does not implement Workspace-wide
  multi-Objective isolation.
- Direct Task-to-Evidence linkage is executable MVP state. Canonical
  Hypothesis, EvidenceRequest, ExecutionRun, AnalysisFrame, evaluation, and
  admission lineage remain **Deferred** to M2/M3-B.

## Implementation gap

- M1-B Planner behavior and M3-A deterministic Data Explorer-to-Evidence
  admission are **Implemented** at bounded library surfaces. M5-A is
  **Partially implemented** for retained in-process cumulative ID-only
  SessionFrame, segmented native PydanticAI conversation continuity, bounded
  pre-build selection, required dependency expansion, and workspace-local
  SQLite research-object composition.
  Authoritative dataset execution context, Evidence admission composition,
  persisted Session recovery, and restart recovery remain **Deferred**.
- `PlanRevision`, `ScientificInvestigationRun`, `InvestigationPlan`,
  `InvestigationProtocol`, `EvidenceRequest`, `DataWorkOrder`,
  `EvaluationBundle`, `ScientificInvestigationOutcome`, `DiscoveryProposal`,
  and `GovernanceDecision` have no supported implementation.
- Hypothesis Analyst and Graph Miner remain unregistered scaffolds. Discovery
  and Hypothesis remain canonical FCO names but have no active MVP runtime.
- Planner successor-state active Objective change and Assumption addition are
  **Implemented** through the application research-state port: new objects are
  persisted before their IDs enter the successor frame. In-place Objective and
  Assumption updates remain **Deferred**. Task persistence supports status
  change only. Active Task values are immutable; changing Task meaning requires
  a new identity, while status change preserves the same identity and
  instruction and is observed on the next context build.
- Application-authority Evidence admission is **Implemented** for the direct
  M3-A Task-to-Evidence contract and **Verified on SQLite**. It is not the
  canonical scientific M3-B admission contract and does not fabricate
  EvidenceRequest, ExecutionRun, AnalysisFrame, or Hypothesis lineage.
- M3-A atomically persists an admitted initial DataProfile with an immutable
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

- Canonical-heavy donor tests for scientific attempts and Discovery retrieval
  are explicitly skipped after the hard cutover. They remain design/test
  material and are not compatibility authority for active schemas.
- The stale pre-M1-B duplicate SessionFrame and `create_plan` context path remain
  removed. The active M1-A SessionFrame schema is the only executable frame
  owner and stores cumulative FCO IDs plus active selectors. The runtime Session
  keeps complete segmented conversation separate, while the current selector
  bounds references before `BuildPlanningContext` resolves authoritative objects
  and required dependencies for the four-node Planner graph. The unregistered
  Hypothesis Analyst, Planner operation contracts, deferred retrieval engine,
  and scientific repositories still contain deferred field references. They
  are not composed into the active M1-A path.
- Fresh SQLite metadata reflects M1-A mappings. Upgrading an existing donor
  database to the hard-cutover schema is **Unsupported**; no production data
  migration is included in this milestone.

## Operational limitation

- Bootstrap composes the in-process S0 dispatcher, bounded Data Explorer, and
  retained runtime Session. The installable `cognieda [PATH]` command reaches
  the development Planner REPL and is **Partially implemented**; session state
  is process-local, and no supported end-to-end Evidence workflow, worker,
  service API, or product CLI exists.
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
- Runtime bootstrap composes the Planner research-object authority at
  `<workspace>/.cognieda/state/cognieda.sqlite3`. The standalone persistence
  helper still retains a provisional package-local default when used outside
  bootstrap without an explicit `COGNIEDA_DB_URL`. Runtime SessionFrame and
  ConversationHistory successors are not automatically persisted, so this
  workspace binding does not establish restart-safe continuity.
- No non-SQLite database is tested.

## Verification gap

- Full pytest collection includes the rewritten M1-B Planner tests. The three
  former donor import blockers were removed rather than restored as
  compatibility APIs.
- A bounded harness proves real dispatcher-compatible Data Explorer execution
  and application Evidence admission. No composed user-to-Planner-to-real-Data
  Explorer-to-Evidence-to-SessionFrame-to-response test exists; M3-A library
  completion does not establish M5-A or MVP-I.
- Focused runtime tests prove cumulative ID-only SessionFrame retention,
  active-selector invariants, authoritative object re-resolution and dependency
  expansion, native `ModelMessage` segment serialization including coherent tool
  call/return and tool-call/retry structure, deterministic Unicode-aware
  selection of four recent turns plus at most four recent older lexical matches
  without deleting or splitting retained segments, separate typed discourse and
  native `message_history` channels used only during request understanding,
  cumulative SessionFrame summary counts, bounded Evidence-absence wording, and
  conversation/Assumption exclusion from empirical answer input. They do not
  prove semantic retrieval, restart-safe Session persistence, or runtime
  Evidence admission composition.
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
