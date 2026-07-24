# Executor Capability Adapter

This package is the non-persistent capability invocation layer used by the durable application
worker. It does not own Planner admission, attempt transitions, result receipt, Evidence admission,
evaluation, governance, Discovery admission, or validity propagation.

## Implemented contracts

| Component | Current role |
| --- | --- |
| `ExecutorInput` | Scientific request with durable ExecutionRun, Task, Hypothesis and DataProfile UUIDs plus the admitted analytical contract |
| `ExecutorContext` | Process-local operational context seam; currently has no concrete fields |
| `ExecutorRegistry` | Registers capability specs and lazy factories, rejects duplicates and caches successful instances |
| `Executor` | Role-neutral LangGraph scaffold used by the unimplemented Graph Miner and Hypothesis Analyst wrappers |
| `DataExplorerExecutor` | Data Explorer-specific LangGraph adapter that validates graph output |
| `ExecutorDispatcher` | Validates claimed attempt identity, builds `ExecutorInput`, invokes one analytical executor, and validates its returned value as `DataExplorerResult` |
| `DataExplorerResult` | Canonical observation-only result imported from `schemas.data_explorer_contracts` |

The durable caller supplies a claimed `PreparedExecution`. The package does not accept Planner state or construct durable contracts.

```python
context = ExecutorContext()
result = await ExecutorDispatcher(executor_registry).dispatch(prepared, context)
```

`prepared` must already contain canonical Task/Hypothesis/DataProfile UUID strings, an `execution_run_id`, dispatch key and lease epoch. `application.orchestrator.dispatcher` reconstructs those values from the persisted run/outbox/FCO records. Calling the adapter with transient Planner handles fails before registry resolution.

## Registration is not runnability

There is no global or default registry. The supported composition root creates one registry and
registers only the deployment-supplied `data_exploration` factory. Graph Miner and Hypothesis
Analyst are not Data Explorer dispatcher capabilities.

`register_factory(...)` exists for explicit lazy factories and test replacement. A factory exception is not cached. The durable worker converts resolution, factory, adapter and executor exceptions into a failed result receipt without creating Evidence or Discovery.

## Boundary rules

- Durable transport and attempt fencing stay in `application.orchestrator`.
- The registry never changes run/outbox/inbox state.
- The dispatcher performs one durable-to-domain conversion.
- Domain input excludes Assumptions, Task motivation, retrieval data, SessionFrame, raw chat, Planner state, repositories and SQL sessions.
- The receiver persists the same canonical observation-only result. The fenced Evidence-admission
  coordinator can create only AnalysisFrame and Evidence.
- Graph Miner and Hypothesis Analyst remain role-neutral, non-runnable scaffolds and do not use the
  Data Explorer result specialization. `ExecutorDispatcher` rejects those capability IDs before
  invocation.

## Removed scaffold APIs

`ExecutionRequest`, `ExecutorOutput`, the duplicate capability-layer `ExecutionResult`, legacy
`ExecutorResult`, and the compatibility bridge were removed. The canonical type is
`schemas.data_explorer_contracts.DataExplorerResult`; `schemas.specialist_contracts` exposes the
same class as part of its public specialist-contract namespace, not as a mirror DTO.

## Not yet implemented

- runnable default executor graphs;
- concrete runtime dependencies or cooperative cancellation in `ExecutorContext`;
- production worker bootstrap;
- delegation/authorization/tracing policy;
- executor-authored Evidence or Discovery (these remain forbidden; executors return observations only).
