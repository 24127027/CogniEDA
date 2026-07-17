# Executor Capability Adapter

This package is the non-persistent capability invocation layer used by the durable application worker. It does not own Planner admission, attempt transitions, result receipt or scientific finalization.

## Implemented contracts

| Component | Current role |
| --- | --- |
| `ExecutorInput` | Scientific request with durable ExecutionRun, Task, Hypothesis and DataProfile UUIDs plus the admitted analytical contract |
| `ExecutorContext` | Process-local operational context seam; currently has no concrete fields |
| `ExecutorRegistry` | Registers capability specs and lazy factories, rejects duplicates and caches successful instances |
| `ExecutorDispatcher` | Validates claimed attempt identity, builds `ExecutorInput`, resolves a factory and calls `executor.run(...)` |
| `ExecutorResult` | Canonical result imported from `application.orchestrator.execution_contracts` |

The durable caller supplies a claimed `PreparedExecution`. The package does not accept Planner state or construct durable contracts.

```python
context = ExecutorContext()
result = await ExecutorDispatcher(executor_registry).dispatch(prepared, context)
```

`prepared` must already contain canonical Task/Hypothesis/DataProfile UUID strings, an `execution_run_id`, dispatch key and lease epoch. `application.orchestrator.dispatcher` reconstructs those values from the persisted run/outbox/FCO records. Calling the adapter with transient Planner handles fails before registry resolution.

## Registration is not runnability

The default registry contains wrappers for `graph_mining` and `hypothesis_testing`, but both graph builders raise `NotImplementedError`. `data_exploration` is catalogued but unregistered. A registered wrapper therefore must not be reported as implemented analytical capability.

`register_factory(...)` exists for explicit lazy factories and test replacement. A factory exception is not cached. The durable worker converts resolution, factory, adapter and executor exceptions into a failed result receipt without creating Evidence or Discovery.

## Boundary rules

- Durable transport and attempt fencing stay in `application.orchestrator`.
- The registry never changes run/outbox/inbox state.
- The dispatcher performs one durable-to-domain conversion.
- Domain input excludes Assumptions, Task motivation, retrieval data, SessionFrame, raw chat, Planner state, repositories and SQL sessions.
- Only the receiver accepts the canonical result, and only `finalize_attempt()` can commit scientific state.

## Removed scaffold APIs

`ExecutionRequest`, `ExecutorOutput` and the duplicate capability-layer `ExecutionResult` were unused scaffold contracts. They were removed after repository-wide call-site review. The canonical result type is `application.orchestrator.execution_contracts.ExecutorResult`; no compatibility execution branch remains.

## Not yet implemented

- runnable default executor graphs;
- concrete runtime dependencies or cooperative cancellation in `ExecutorContext`;
- production worker bootstrap;
- delegation/authorization/tracing policy;
- executor-authored Evidence or Discovery (these remain forbidden; executors return observations only).
