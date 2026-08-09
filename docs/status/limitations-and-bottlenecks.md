# Limitations and bottlenecks

These are verified constraints of the M1-A implementation, not a sprint
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

- M1-B Planner behavior, M3-A real Data Explorer-to-Evidence integration, and
  M5-A single-session composition are **Deferred**.
- `PlanRevision`, `ScientificInvestigationRun`, `InvestigationPlan`,
  `InvestigationProtocol`, `EvidenceRequest`, `DataWorkOrder`,
  `EvaluationBundle`, `ScientificInvestigationOutcome`, `DiscoveryProposal`,
  and `GovernanceDecision` have no supported implementation.
- Hypothesis Analyst and Graph Miner remain unregistered scaffolds. Discovery
  and Hypothesis remain canonical FCO names but have no active MVP runtime.
- Objective and Assumption update behavior is **Deferred** to M1-B. Task
  persistence supports status change only. Active Task values are immutable;
  changing Task meaning requires a new identity, while status change produces
  a replacement with the same identity and instruction.
- Evidence creation from Data Explorer output and sole application-authority
  admission are not implemented. The active frame and SQLite repository
  boundaries admit Evidence only for a `COMPLETED` Task; incomplete or failed
  work cannot produce admitted MVP Evidence.
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
- The local Data Explorer donor path can execute bounded analysis or profiling
  from a direct request. It is not a production sandbox and is not connected
  to Evidence admission.
- Profiling describes the active dataset without duplicate removal, null-row
  removal, or input mutation. Actual cleaning and transformation remain
  blocked until successor dataset and DataProfile semantics exist.
- `DATA_TRANSFORMATION` remains blocked until immutable successor dataset state
  and successor DataProfile handling exist.
- Planner-to-dispatch adapter tests use a registered fake provider; they do not
  prove model-selected real Data Explorer work.

## Database limitation

- Current bounded persistence is **Verified on SQLite** only.
- Durable restart/resume, replay, claims, leases, result inbox, and multi-store
  migration are outside M1-A.
- SessionFrame snapshots use an internal serialized SQLite envelope; this is a
  bounded round-trip seam, not M5-A/M5-B durable runtime authority.
- No non-SQLite database is tested.

## Verification gap

- Full pytest collection is interrupted by three pre-existing M1-B Planner
  donor mismatches involving `TaskManagementDraft`, `route_intent`,
  `understand_request`, `ChildTaskProposalDraft`, and `manage_tasks`.
- Excluding exactly those three modules, the PR #36 layer-boundary run recorded
  133 passes and 57 explicit deferred-donor skips.
- No end-to-end user-to-Planner-to-real-Data Explorer-to-Evidence-to-
  SessionFrame-to-response test exists; that is not an M1-A completion claim.
- No production performance envelope, non-SQLite validation, external
  integration test, or first-party Markdown link-check command exists.

## Unsupported feature

- DVC execution, graph-database integration, external MCP services, service
  APIs, UI, and the product CLI are **Unsupported**.
- Cross-Objective Evidence reuse and cross-Objective relation admission have
  no supported path and must remain fail closed.
- Production bounded Python execution, full analytical tool coverage,
  streaming, multi-session coordination, and successor transformation remain
  **Deferred**.

## Documentation limitation

- Current status is a dated source/test audit and can drift when runtime code
  changes. Capability changes must update this status track in the same change.
- Source-layout documentation describes implementation ownership only and does
  not redefine the canonical target or executable MVP subset.
