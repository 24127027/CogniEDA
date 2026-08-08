# Current state

This page answers one question: **what is supported on current `main`?** It
describes the source at `origin/main` commit
`711ab9bc7b1e7b209199c21cdf8ea8b1597d040f`, inspected on 2026-08-08. A
schema, interface, stub, fixture, configuration entry, or directory is not
treated as a supported workflow by itself.

The canonical architecture remains the target. Use the
[documentation index](../index.md) for that model and
[Limitations and bottlenecks](limitations-and-bottlenecks.md) for present
constraints.

## Capability summary

| Reader-visible capability | Status | Current boundary |
| --- | --- | --- |
| Runtime entry boundary | **Unsupported** | The installed `cognieda` script calls `main.py`, which only prints a placeholder message. There is no composed user-facing runtime, service, or application request pipeline. |
| Workspace and Objective support | **Partially implemented** (**Verified on SQLite**) | A database URL can identify an isolated local store. `Objective` has schema, table, repository CRUD, and `ObjectiveRevision` provenance. Tasks and other state are not Objective-bound, and no Workspace initializer, registry, or active-session authority exists. |
| Current FCO schemas and persistence | **Partially implemented** (**Verified on SQLite**) | All eight named FCOs have Pydantic schemas and SQLModel records. Repository surfaces exist, but the current shapes and relationships do not fully implement the canonical contracts described below. |
| Planner support | **Partially implemented** (**Verified on SQLite**) | Request classification, explicit-command parsing, bounded Task creation and decomposition proposals, durable `PlannerOperation` approval/resume, and bounded atomic commit are exercised. Planner now accepts `PlannerDeps` (terminal printer), can invoke built-in tools (starting with terminal printer), and tool calling succeeds. Question answering, question proposal, task selection, execution preparation with executor dispatch, and execution review remain stubs. |
| `PlanRevision` | **Unsupported** | No canonical `PlanRevision`, plan binding, dependency, assignment, activation, or plan-version persistence is present. `ObjectiveRevision` is Objective-change provenance and is not a substitute. |
| Task taxonomy | **Known limitation** | Current `TaskKind` is `ANALYTICAL`, `ORGANIZING`, and `REVIEW`, not canonical `DATA`, `SCIENTIFIC`, `GRAPH`, and `SYNTHESIS`. Current Task records also carry `profile_id`, `variables`, and `evidence_expectation`, which the target assigns outside semantic Task identity. |
| Executor registry and dispatch | **Partially implemented** | Capability identifiers are now lightweight `StrEnum` values instead of metadata specs. Registry uses `Capability` enum to map to executor factories, caches executor instances by provider for reuse across capabilities, and supports one executor providing multiple capabilities. Dispatcher dependency protocol exists for delegation tools. Planner integration remains absent. |
| Tool and skill assembly | **Partially implemented** | `ToolManager` can assemble caller-selected built-ins and resolve configured MCP and skill entries. Built-in tools now include a terminal printer (`print_to_terminal`) for testing. Dependency protocols exist (`HasExecutorDispatcher`, `HasTerminalPrinter`) enabling tool access to shared services. Configured skill directories are absent, MCP worker names do not resolve to enabled servers, and no complete composed runtime proves all agent use. |
| Data Explorer | **Unsupported** | Dataframe/file loading and deterministic profiling utilities exist, but no registered runnable Data Explorer or role-native `DataWorkOrder -> DataExplorerResult` boundary exists. `data_exploration` is only catalogued. |
| Hypothesis Analyst | **Unsupported** | A wrapper and capability registration exist, but its default graph raises `NotImplementedError`. The wrapper currently selects a dataset tool, contrary to the canonical no-direct-dataset-access boundary; no supported scientific controller path uses it. |
| Graph Miner | **Unsupported** | A wrapper and registration exist, but its default graph raises `NotImplementedError`. No supported read-only graph-inquiry workflow is composed. |
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
- operational execution foundations are not connected to runnable specialists
  or result admission.

No legacy fallback is considered supported. Missing canonical contracts must
fail closed when implementation reaches those boundaries.

## Verification qualification

The focused current-capability selection produced **115 passes and 2
failures**; the full suite produced **127 passes and the same 2 failures**.
Both failures expose existing contract drift: one stops at the missing
`PlannerOutput.executor_dispatch_ref` field, and one shows that
`PlannerOutput` has no nested execution-request field through which capability
validation can run. Source inspection also confirms that `ExecutorOutput`
lacks the scientific-result fields the first contract test would check next.
These are verification gaps, not documentation-change regressions, and are
listed in
[Limitations and bottlenecks](limitations-and-bottlenecks.md).

## Recent MVP progress (2026-08-08)

The following refactors advance toward MVP tool-calling capability:

- **Capability system simplification**: Replaced metadata-heavy `CapabilitySpec` dataclass with lightweight `Capability` `StrEnum`. Registry now maps capabilities to executor factories and caches instances by provider, allowing one executor to provide multiple capabilities.
- **Executor types cleanup**: Removed planned-ahead schemas (`ExecutorOutput` with extensive optional fields). Simplified `ExecutionResult` to only essential fields (`hypothesis`, `evidence`, `discoveries`, `data_profile`). Placeholder schemas for `DataProfile`, `Discovery`, `Evidence`, `Hypothesis`, `Task` are in place pending canonical schema implementation.
- **Built-in tools organization**: Renamed `builtin_tools/` → `builtin/` for clarity. Added `terminal.py` with `print_to_terminal` tool for MVP testing.
- **Dependency protocols for tools**: Introduced `HasExecutorDispatcher` and `HasTerminalPrinter` protocols. Tools now access shared services via `RunContext.deps`, enabling delegation to executors and terminal output.
- **Planner dependency injection**: `Planner` now accepts `PlannerDeps` (containing `RichTerminalPrinter`). `PlannerModel` receives dependencies and builtin tools, enabling tool invocation during planning.
- **Tool calling validated**: Planner successfully invokes the terminal tool. This marks the first end-to-end MVP milestone for agent tool calling.

Current boundary: Tool calling works for built-in tools. Executor dispatch remains a stub dependency; full executor integration and Evidence admission are next.
