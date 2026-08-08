# Current state

This page answers one question: **what is supported on current `main`?** It
describes the S0 worktree based on `origin/main` commit
`e666276ceb37b21a7b787dd162c96dce43f0db07`, inspected on 2026-08-09. A
schema, interface, stub, fixture, configuration entry, or directory is not
treated as a supported workflow by itself.

The canonical architecture remains the target. Use the
[documentation index](../index.md) for that model and
[Limitations and bottlenecks](limitations-and-bottlenecks.md) for present
constraints.

## Capability summary

| Reader-visible capability | Status | Current boundary |
| --- | --- | --- |
| Runtime entry boundary | **Unsupported** | The installed `cognieda` script opens a development REPL and bootstrap now composes the in-process S0 dispatcher. This is not a supported product CLI, service, or complete research-state request pipeline. |
| Workspace and Objective support | **Partially implemented** (**Verified on SQLite**) | A database URL can identify an isolated local store. `Objective` has schema, table, repository CRUD, and `ObjectiveRevision` provenance. Tasks and other state are not Objective-bound, and no Workspace initializer, registry, or active-session authority exists. |
| Current FCO schemas and persistence | **Partially implemented** (**Verified on SQLite**) | All eight named FCOs have Pydantic schemas and SQLModel records. Repository surfaces exist, but the current shapes and relationships do not fully implement the canonical contracts described below. |
| Planner support | **Partially implemented** | The active Planner graph has one model-backed `create_plan` node. `PlannerDeps` exposes terminal and dispatcher protocols, and the model receives terminal and data-delegation tools. The current graph does not implement the canonical Planner pipeline, consume `PlannerWorkOutcome`, or connect durable operation approval/commit services to execution. |
| `PlanRevision` | **Unsupported** | No canonical `PlanRevision`, plan binding, dependency, assignment, activation, or plan-version persistence is present. `ObjectiveRevision` is Objective-change provenance and is not a substitute. |
| Task taxonomy | **Known limitation** | Current `TaskKind` is `ANALYTICAL`, `ORGANIZING`, and `REVIEW`, not canonical `DATA`, `SCIENTIFIC`, `GRAPH`, and `SYNTHESIS`. Current Task records also carry `profile_id`, `variables`, and `evidence_expectation`, which the target assigns outside semantic Task identity. |
| Executor registry and dispatch | **Implemented** | The S0 library boundary uses one typed `Capability` enum, explicit dependency-aware provider factories, multi-capability mapping, lazy provider reuse, duplicate-registration rejection, typed async dispatch, fail-closed missing registration, and controlled provider errors. It does not implement admission, leases, retry, or distributed routing. |
| Tool and skill assembly | **Partially implemented** | `ToolManager` can assemble caller-selected built-ins and resolve configured MCP and skill entries. Protocol dependencies expose terminal and dispatcher services. A PydanticAI data-delegation adapter is registered for Planner and is tested through dispatcher to a registered fake provider without a model endpoint. Configured skill directories and external MCP composition remain absent. |
| Data Explorer | **Partially implemented** | Bootstrap explicitly maps `DATA_ANALYSIS`, `DATA_PROFILING`, and `DATA_TRANSFORMATION` to one reusable Data Explorer provider. Local analysis and profiling donor paths return typed `DataExplorerResult` observations or DataProfile candidates for the current legacy Task plus dataset-path boundary. They do not create Evidence. There is no canonical `DataWorkOrder`, application-authority admission, or end-to-end Planner workflow. Transformation is registered but returns a typed blocker until successor dataset/DataProfile semantics exist. |
| Hypothesis Analyst | **Unsupported** | The donor wrapper imports but is deliberately not registered as a runnable provider. Its scientific workflow and application-authority contracts remain deferred. |
| Graph Miner | **Unsupported** | The wrapper imports but is deliberately not registered; its graph runtime remains unimplemented. No supported read-only graph-inquiry workflow is composed. |
| `ScientificInvestigationRun` | **Unsupported** | No schema, repository, lifecycle service, or runtime path exists. |
| `InvestigationPlan` and `InvestigationProtocol` | **Unsupported** | No canonical plan, protocol, protocol revision, or scientific operationalization record exists. |
| `EvidenceRequest` and `DataWorkOrder` | **Unsupported** | No role-native request/work-order schemas, admission path, or request-to-attempt workflow exists. |
| `ExecutionRun` and `AnalysisFrame` | **Partially implemented** (**Verified on SQLite**) | Both have schemas, SQLModel tables, and repositories. `ExecutionRun` also has admission/outbox, lease, fencing, cancellation, and retry foundations. They are not composed into a complete executor-to-Evidence workflow. |
| Evidence admission | **Partially implemented** (**Verified on SQLite**) | Immutable Evidence schemas and repository persistence exist. Optional strict mode dereferences `AnalysisFrame` and `ExecutionRun` and checks selected lineage matches; default repository construction does not enable strict validation, and there is no sole application-authority admission service for canonical executor results. |
| Protected evaluation | **Partially implemented** | `SessionContextBuilder` and retrieval policy exclude Assumptions, Tasks, prior Discoveries, invalid Evidence, stale context, and caches from conclusion/discovery-synthesis projections. There is no canonical `EvaluationBundle`, Hypothesis Analyst evaluation workflow, or Objective-bound protected evaluator. |
| `DiscoveryProposal` | **Unsupported** | No proposal schema, persistence, or scientific proposal workflow exists. |
| Typed scientific outcomes | **Unsupported** | No `ScientificInvestigationOutcome` or canonical typed non-Discovery outcome record exists. Discovery enums contain inconclusive labels, but an enum value is not the governed outcome lifecycle. |
| Governance | **Unsupported** | Planner-operation approval is implemented for a bounded mutation flow, but canonical scientific governance over an exact `DiscoveryProposal` is absent. |
| Discovery admission | **Partially implemented** (**Verified on SQLite**) | Schema and repository guards require an existing Hypothesis, non-empty active same-Hypothesis Evidence, structured validity basis, and no existing Discovery. Direct repository creation does not require a governance decision, canonical proposal identity, or valuable-inconclusive eligibility proof, so it is not the complete admission boundary. |
| Cardinality enforcement | **Partially implemented** (**Verified on SQLite**) | Current repository checks and fresh-schema uniqueness constraints enforce at most one Hypothesis per current legacy-eligible Task and at most one Discovery per Hypothesis. The Task-side guard uses the legacy taxonomy and scientific fields, and the SQLite upgrade helper does not add these constraints to older databases. |
| Validity propagation | **Partially implemented** (**Verified on SQLite**) | Repository methods can supersede DataProfiles and Evidence, invalidate Evidence, mark directly scoped Evidence historical, and flag dependent Discoveries when related repositories share a session. The sequence commits in separate repository steps and does not implement complete typed, atomic, Objective-scoped propagation or restoration. |
| `SessionFrame` | **Partially implemented** (**Verified on SQLite**) | Schema, append-only repository, builder, and four local projections exist. Frames lack explicit Objective identity, purpose, reasoning-mode, scope, lifecycle-point, and validity-basis binding; latest/recent queries are store-wide. |
| Recovery and replay | **Partially implemented** (**Verified on SQLite**) | Pending Planner operation batches can be reloaded by exact IDs and session, and execution attempts have outbox, lease, fencing, cancellation, and one-successor retry controls. There is no result inbox, complete replay protocol, canonical plan/investigation reconstruction, or end-to-end restart-safe runtime. |
| Database support | **Verified on SQLite** | The default store is workspace-local SQLite; foreign keys and repository behavior are tested there. The engine accepts other SQLAlchemy URLs, but no other database is verified, and the targeted upgrade helper is SQLite-only. |
| CLI support | **Unsupported** | The declared `cognieda` entry point is a placeholder. `db.init_db` is an internal initialization helper, not a supported product CLI. |
| External integrations | **Unsupported** | DVC execution is an explicit not-implemented boundary. MCP entries are commented examples or unresolved worker references, and no supported external service, graph store, model-backed end-to-end workflow, or deployment adapter is composed. |

## Supported schema and repository boundary

The eight current FCO schemas are `Objective`, `DataProfile`, `Assumption`,
`Task`, `Hypothesis`, `Evidence`, `Discovery`, and `SessionFrame`. Non-FCO
records currently include `ObjectiveRevision`, `UserDecision`,
`PlannerOperation`, `AnalysisFrame`, `ExecutionRun`, `ExecutionApproval`, and
`ExecutionOutbox`. Their existence proves typed local state and repository
behavior, not the complete canonical lifecycle.

Within that boundary, current tests exercise:

- immutable Pydantic payloads for `DataProfile`, `Evidence`, and `Discovery`;
- SQLite foreign-key behavior and separate-store isolation;
- repository creation and query paths for FCO and provenance records;
- legacy Task-to-Hypothesis and Hypothesis-to-Discovery upper bounds;
- bounded Planner proposal approval, resume, commit, and rollback behavior;
- execution-attempt admission, outbox, leases, fencing, cancellation, and retry;
- local context projections and invalid-state exclusions;
- deterministic baseline profiling for supported local tabular inputs.

These are library and persistence surfaces. They are not exposed as a
supported user workflow.

## Current drift from the canonical target

The most consequential drift is structural:

- Task identity and taxonomy predate the canonical plan/science separation.
- Planner-owned Task fields still encode scientific operationalization.
- the canonical scientific investigation, Evidence-request, protected
  evaluation, governance, and proposal records do not exist;
- direct repository calls can persist Evidence or Discovery without the full
  application-authority admission sequence;
- context and retrieval records are not explicitly Objective-bound;
- the bounded dispatcher is connected to a local Data Explorer donor provider,
  but no specialist result is connected to canonical admission.

No legacy fallback is considered supported. Missing canonical contracts must
fail closed when implementation reaches those boundaries.

## Verification qualification

The focused S0 selection produced **24 passes**. The full `pytest -q` gate is
interrupted during collection by three donor-state Planner test/source
mismatches: tests import `TaskManagementDraft`, `route_intent`,
`understand_request`, `ChildTaskProposalDraft`, and `manage_tasks`, while the
starting PR #31 merge contains none of those source symbols. The affected
source and test files have byte-identical Git hashes to the starting
`e666276` versions. With those three pre-existing files excluded, the remaining
repository suite produces **111 passes**. This qualification is listed in
[Limitations and bottlenecks](limitations-and-bottlenecks.md).

## S0 executor stabilization (2026-08-09)

S0 replaced donor-state ambiguity with one executable foundation:

- `Capability` is the only active capability identity and requests do not carry
  redundant executor identity;
- explicit composition owns provider registration; importing specialist
  modules no longer mutates a global registry;
- the dispatcher calls a role provider asynchronously and returns its
  role-native result;
- executor types use the real project Task contract and no longer redefine fake
  FCO schemas;
- shared `ExecutionResult` is non-semantic transport metadata;
  `DataExplorerResult` owns Data Explorer fields;
- a minimal `PlannerWorkOutcome` projection seam exists, while Planner
  consumption remains **Deferred**;
- transformation fails closed rather than mutating the active dataset state.

Current boundary: the capability-to-provider infrastructure and deterministic
tool-adapter proof are **Implemented**. Full Data Explorer MVP, canonical
Evidence admission, scientific routing, Graph Miner runtime, and end-to-end
Planner consumption remain **Unsupported** or **Deferred** as listed above.

## Design target: Dependency inversion

The target architecture separates dependency contracts from implementations:

- Core agents depend on protocols such as `TerminalPrinter` and the dispatcher
  port; the final target package placement remains unresolved.
- Bootstrap wires concrete implementations with injected dependencies.
- Agents remain testable and composable; tests can substitute mock implementations.
- Adapter layer (`RichTerminalPrinter`, CLI adapters, integrations) lives in boundary packages, not core modules.

This refactor is established design target but deferred post-MVP. See [Persistence and admission](../architecture/persistence-and-admission.md#dependency-inversion-and-role-boundaries) for structure details.
