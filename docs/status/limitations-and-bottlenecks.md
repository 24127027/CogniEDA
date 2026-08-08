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
- A bounded `DataExplorerResult` and Planner projection seam exist, but the
  canonical work-order, specialist, governance, and admission contract family
  is incomplete.

## Implementation gap

- `PlanRevision`, `ScientificInvestigationRun`, `InvestigationPlan`,
  `InvestigationProtocol`, `EvidenceRequest`, `DataWorkOrder`,
  `EvaluationBundle`, `ScientificInvestigationOutcome`, `DiscoveryProposal`,
  and `GovernanceDecision` have no current supported implementation.
- Planner execution nodes remain incomplete. Hypothesis Analyst and Graph Miner
  are import-safe scaffolds and are deliberately not registered as runnable.
- The three pre-existing Planner donor/test mismatches belong to M1-B unless
  they block M1-A test collection earlier; they do not establish an S0 executor
  regression or a separate repair milestone.
- Evidence and Discovery repository guards are not composed behind complete
  application-authority admission services.
- There is no result-inbox or canonical result-to-Evidence workflow.

## Operational limitation

- Bootstrap composes the in-process S0 registry and dispatcher, but there is no
  supported end-to-end application runtime, worker process, or service API.
- Planner is configured with built-in tool adapters, and the data-capability
  adapter is tested through dispatcher to a registered fake provider. This is
  an invocation-seam proof, not completed MVP Planner behavior.
- The local Data Explorer donor provider can produce a typed result from a
  direct capability request, but it is not connected to execution-attempt
  records, outbox controls, or admission.
- Configuration mentions skills and MCP workers that do not establish a working external integration by themselves. The configured skill directories are absent from the current tree.
- Delegation adapter dispatch is tested with a fake provider; real Planner to
  Data Explorer to admission integration remains incomplete.

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

- Data Explorer is runnable only through its bounded local donor path;
  Hypothesis Analyst and Graph Miner have no registered runtime provider.
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

- The focused S0 selection recorded 24 passing tests. The full S0 suite was
  interrupted by three pre-existing Planner collection mismatches: tests
  import `TaskManagementDraft`, `route_intent`, `understand_request`,
  `ChildTaskProposalDraft`, and `manage_tasks`, which the corresponding Planner
  source does not define. Those files were unchanged by S0, so this is not an
  S0 executor regression.
  Excluding those three files, the S0 report recorded 111 passing tests.
  Ownership is M1-B unless the collection failure blocks M1-A earlier.
- PydanticAI delegation adapter to dispatcher to a registered fake provider is
  validated. This does not cover model-selected real Data Explorer work or
  specialist result admission.
- No non-SQLite database is tested.
- No end-to-end user, specialist, governance, admission, recovery, or
  external-integration test exists. CLI remains unsupported.
- The current repository has no first-party Markdown link-check command.

## Documentation limitation

- Current status is a dated source audit and can drift when runtime code
  changes. Capability changes must update this track in the same change.
- Compatibility notices preserve old inbound paths but intentionally do not
  repeat the canonical explanation.
