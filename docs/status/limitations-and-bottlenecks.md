# Limitations and bottlenecks

These are verified constraints of current `main`, not a sprint backlog. The
[current-state page](current-state.md) owns capability detail; this page groups
the consequences by limitation type.

## Architectural gap

- Current Task identity combines coordination and scientific fields and uses
  the legacy `ANALYTICAL/ORGANIZING/REVIEW` taxonomy. The canonical separation
  among Task, PlanRevision, plan bindings, and scientific operationalization is
  therefore not represented.
- Current schemas do not bind most durable state to an Objective. Multiple
  Objectives can be stored, but exact Objective isolation cannot be enforced
  across Tasks, scientific state, retrieval, or SessionFrames.
- Canonical role-native contracts among Planner, Data Explorer, Hypothesis
  Analyst, Graph Miner, governance, and application authority are absent.

## Implementation gap

- `PlanRevision`, `ScientificInvestigationRun`, `InvestigationPlan`,
  `InvestigationProtocol`, `EvidenceRequest`, `DataWorkOrder`,
  `EvaluationBundle`, `ScientificInvestigationOutcome`, `DiscoveryProposal`,
  and `GovernanceDecision` have no current supported implementation.
- Planner execution nodes and both registered specialist graphs are stubs.
- Evidence and Discovery repository guards are not composed behind complete
  application-authority admission services.
- There is no result-inbox or canonical result-to-Evidence workflow.

## Operational limitation

- There is no composed application runtime, worker process, or service API.
- Planner can now invoke built-in tools (MVP milestone: tool calling validated as of 2026-08-08).
- Execution-attempt records and outbox controls cannot yet produce a result through a runnable default specialist.
- Configuration mentions skills and MCP workers that do not establish a working external integration by themselves. The configured skill directories are absent from the current tree.
- Executor dispatch through delegation tools is the immediate next step; full specialist integration remains incomplete.

## Database limitation

- Current behavior is **Verified on SQLite** only.
- The execution-attempt upgrade helper applies only to SQLite.
- Older databases are not upgraded to all fresh-schema cardinality
  constraints; creating tables from metadata is not a general migration plan.
- JSON-held reference lists cannot receive the same database foreign-key
  enforcement as typed columns.

## Recovery limitation

- Planner proposal resumption covers exact pending operation IDs, not complete
  Objective or plan reconstruction.
- Execution attempts have outbox, lease, fencing, and retry foundations but no
  durable result inbox or end-to-end replay path.
- SessionFrame latest/recent lookup is store-wide rather than Objective-bound.

## Unsupported feature

- Data Explorer, Hypothesis Analyst, and Graph Miner are not runnable through a
  supported current workflow.
- DVC execution, graph-database integration, external MCP services, service
  APIs, and the product CLI are unsupported.
- Cross-Objective Evidence reuse and cross-Objective relation admission have no
  supported path and must remain fail closed.

## Performance bottleneck

- No production performance envelope has been established. Repository queries
  and context assembly are exercised only at test scale.
- Discovery retrieval performs bounded relational filtering followed by local
  lexical scoring; no scale, latency, or quality benchmark supports a broader
  claim.
- JSON collections and store-wide SessionFrame queries may become expensive,
  but their production impact has not been measured.

## Verification gap

- The focused current-capability selection passed 115 tests and failed 2
  existing contract tests; the full suite passed 127 tests and failed the same
  2 tests. One stops at the missing
  `PlannerOutput.executor_dispatch_ref`; the other expects nested
  execution-request capability validation through `PlannerOutput`, which has
  no such field. `ExecutorOutput` also lacks the scientific-result fields that
  the first contract test would check after the Planner assertion passes.
- MVP tool calling is now validated (2026-08-08): Planner successfully invokes
  built-in tools through pydantic_ai tool registration. This does not yet cover
  full executor dispatch through tools or specialist result admission.
- No non-SQLite database is tested.
- No end-to-end user, specialist, governance, admission, recovery, or
  external-integration test exists. CLI remains unsupported.
- The current repository has no first-party Markdown link-check command.

## Documentation limitation

- Current status is a dated source audit and can drift when runtime code
  changes. Capability changes must update this track in the same change.
- Compatibility notices preserve old inbound paths but intentionally do not
  repeat the canonical explanation.
