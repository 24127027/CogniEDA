# Data Explorer Runtime Adapter

This package is the non-persistent Data Explorer adapter invocation layer used by the durable application
worker. It does not own Planner admission, attempt transitions, result receipt, Evidence admission,
evaluation, governance, Discovery admission, or validity propagation.

## Purpose and authority

The package validates one application-prepared execution contract, resolves exactly one configured
Data Explorer adapter, invokes it, and validates one observation-only result. It has no durable
writer or transaction authority.

## Implemented contracts

| Component | Current role |
| --- | --- |
| `DataExplorerInput` | Scientific request with durable ExecutionRun, Task, Hypothesis and DataProfile UUIDs plus the admitted analytical contract |
| `DataExplorerExecutionContext` | Process-local operational context seam; currently has no concrete fields |
| `DataExplorerAdapterProtocol` | Narrow role-specific `run(input, context) -> DataExplorerResult` boundary accepted by dispatch |
| `DataExplorerRegistry` | Registers exactly one explicit Data Explorer executor id and lazy factory per runtime, rejects any second registration, validates the constructed adapter, and caches the successful instance |
| `DataExplorerAdapter` | Data Explorer-specific LangGraph adapter that validates graph output as `DataExplorerResult` |
| `DataExplorerDispatcher` | Validates claimed attempt identity, builds `DataExplorerInput`, invokes one configured Data Explorer adapter, and validates its returned value as `DataExplorerResult` |
| `DataExplorerResult` | Canonical observation-only result imported from `schemas.execution.data_explorer` |

The durable caller supplies a claimed `PreparedExecution`. The package does not accept Planner state or construct durable contracts.

## Happy path

```python
context = DataExplorerExecutionContext()
result = await DataExplorerDispatcher(data_explorer_registry).dispatch(prepared, context)
```

`prepared` must already contain canonical Task/Hypothesis/DataProfile UUID strings, an `execution_run_id`, dispatch key and lease epoch. `application.execution.dispatch` reconstructs those values from the persisted run/outbox/FCO records. Calling the adapter with transient Planner handles fails before registry resolution.

## Registration is not runnability

There is no global or default registry. The supported composition root creates one private registry
and registers the deployment-supplied Data Explorer factory under its explicit executor id. That id
must exactly match the `executor_id` reconstructed from durable run/outbox state; there is no
fallback adapter. The current admitted analytical contract permits `deterministic`, so a runtime
intended to execute current planner work must configure that exact id.

`register_factory(...)` is an ordinary method, not a decorator. A factory exception or malformed
factory product is not cached. The durable worker converts resolution, factory, adapter and
invocation exceptions into a failed result receipt without creating Evidence or Discovery. Graph
Miner and Hypothesis Analyst have no registry entry or package-level executor alias.

## Failure and recovery

Registry, factory, adapter, invocation, and result-validation failures remain technical. The
application worker converts them to `DataExplorerFailureResult`, and
`application.execution.receiver` persists the fenced receipt. This package does not reclaim leases,
authorize retries, finalize Evidence, or recover durable state.

## Forbidden responsibilities and boundary rules

- Durable transport and attempt fencing stay in `application.execution`.
- The registry never changes run/outbox/inbox state.
- The dispatcher performs one durable-to-domain conversion.
- Domain input excludes Assumptions, Task motivation, retrieval data, SessionFrame, raw chat, Planner state, repositories and SQL sessions.
- The receiver persists the same canonical observation-only result. The fenced Evidence-admission
  coordinator can create only AnalysisFrame and Evidence.
- Graph Miner and Hypothesis Analyst remain outside Data Explorer dispatch and do not use the
  Data Explorer result specialization. Their identifiers fail exact registry lookup.

## Transaction, retry, replay, and fencing ownership

This package owns no transaction. `application.execution.ExecutionAttemptTransitionService` owns
run/outbox/inbox protocol writes and fencing. Technical retry creates a new durable attempt before
this adapter layer is invoked again. Duplicate/replayed result classification occurs after dispatch
at the authoritative receiver/transition boundary.

## Removed generic executor symbols

Generic `ExecutorRegistry`, `ExecutorDispatcher`, `ExecutorInput`, and `ExecutorContext` names were
replaced by role-specific `DataExplorer*` symbols. `DataExplorerExecutor`,
`GraphMinerExecutor`, `HypothesisAnalystExecutor`, the generic executor state, decorator
registration, cross-specialist capability-selection helpers, `ExecutionRequest`, `ExecutorOutput`,
the duplicate capability-layer `ExecutionResult`, legacy `ExecutorResult`, and compatibility
bridges were removed. The canonical output type is
`schemas.execution.data_explorer.DataExplorerResult`.

## Tests

- `tests/executor/test_registry_dispatcher.py`
- `tests/application/test_runtime_composition.py`
- `tests/architecture/test_architecture_enforcement.py`
- `tests/e2e/test_research_lineage.py`

## Limitations and not yet implemented

- runnable default executor graphs;
- concrete runtime dependencies or cooperative cancellation in `DataExplorerExecutionContext`;
- production worker bootstrap;
- deployment-supplied authentication, Analyst model, and concrete Data Explorer adapters;
- delegation/authorization/tracing policy;
- executor-authored Evidence or Discovery (these remain forbidden; executors return observations only).

The local runtime and validity facade are SQLite-only, expose no supported CLI, and do not start a
worker or service loop. Package S1-B moved execution coordination to `application.execution`,
Evidence admission to `application.evidence`, and canonical execution contracts to
`schemas.execution`. S2/S3 decomposition of the remaining evaluation, governance, Discovery, and
validity responsibilities is deferred.
