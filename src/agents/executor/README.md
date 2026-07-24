# Data Explorer Capability Adapter

This package is the non-persistent Data Explorer capability invocation layer used by the durable application
worker. It does not own Planner admission, attempt transitions, result receipt, Evidence admission,
evaluation, governance, Discovery admission, or validity propagation.

## Implemented contracts

| Component | Current role |
| --- | --- |
| `DataExplorerInput` | Scientific request with durable ExecutionRun, Task, Hypothesis and DataProfile UUIDs plus the admitted analytical contract |
| `DataExplorerExecutionContext` | Process-local operational context seam; currently has no concrete fields |
| `DataExplorerRegistry` | Registers Data Explorer capability specs and lazy factories, rejects duplicates and caches successful instances |
| `DataExplorerAdapter` | Data Explorer-specific LangGraph adapter that validates graph output as `DataExplorerResult` |
| `DataExplorerDispatcher` | Validates claimed attempt identity, builds `DataExplorerInput`, invokes one configured Data Explorer adapter, and validates its returned value as `DataExplorerResult` |
| `DataExplorerResult` | Canonical observation-only result imported from `schemas.data_explorer_contracts` |

The durable caller supplies a claimed `PreparedExecution`. The package does not accept Planner state or construct durable contracts.

```python
context = DataExplorerExecutionContext()
result = await DataExplorerDispatcher(data_explorer_registry).dispatch(prepared, context)
```

`prepared` must already contain canonical Task/Hypothesis/DataProfile UUID strings, an `execution_run_id`, dispatch key and lease epoch. `application.orchestrator.dispatcher` reconstructs those values from the persisted run/outbox/FCO records. Calling the adapter with transient Planner handles fails before registry resolution.

## Registration is not runnability

There is no global or default registry. The supported composition root creates one private registry and
registers only the deployment-supplied `data_exploration` factory. Graph Miner and Hypothesis
Analyst are not Data Explorer dispatcher capabilities and are not registered in this registry.

`register_factory(...)` exists for explicit lazy factories and test replacement. A factory exception is not cached. The durable worker converts resolution, factory, adapter and executor exceptions into a failed result receipt without creating Evidence or Discovery.

## Boundary rules

- Durable transport and attempt fencing stay in `application.orchestrator`.
- The registry never changes run/outbox/inbox state.
- The dispatcher performs one durable-to-domain conversion.
- Domain input excludes Assumptions, Task motivation, retrieval data, SessionFrame, raw chat, Planner state, repositories and SQL sessions.
- The receiver persists the same canonical observation-only result. The fenced Evidence-admission
  coordinator can create only AnalysisFrame and Evidence.
- Graph Miner and Hypothesis Analyst remain outside Data Explorer dispatch and do not use the
  Data Explorer result specialization. `DataExplorerDispatcher` rejects those capability IDs before
  invocation.

## Removed generic executor symbols

Generic `ExecutorRegistry`, `ExecutorDispatcher`, `ExecutorInput`, and `ExecutorContext` names were replaced by role-specific `DataExplorer*` symbols. `ExecutionRequest`, `ExecutorOutput`, the duplicate capability-layer `ExecutionResult`, legacy `ExecutorResult`, and compatibility bridges were removed. The canonical type is `schemas.data_explorer_contracts.DataExplorerResult`.

## Not yet implemented

- runnable default executor graphs;
- concrete runtime dependencies or cooperative cancellation in `DataExplorerExecutionContext`;
- production worker bootstrap;
- delegation/authorization/tracing policy;
- executor-authored Evidence or Discovery (these remain forbidden; executors return observations only).
