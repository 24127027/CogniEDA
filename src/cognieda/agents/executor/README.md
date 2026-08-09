# Executor package

The executor package is **Implemented** only at the bounded S0 capability,
registry, dispatcher, provider-factory, tool-adapter, and bootstrap-composition
surface.

`DATA_ANALYSIS`, `DATA_PROFILING`, and `DATA_TRANSFORMATION` explicitly map to
one reusable Data Explorer provider. Analysis and profiling retain narrow local
donor behavior. Transformation is registered but fails closed until a new
dataset state and successor DataProfile can be produced. Hypothesis Analyst and
Graph Miner import as deferred scaffolds and are not registered as runnable.

Shared `ExecutionResult` is non-semantic transport metadata. Specialist fields
belong to role-native results such as `DataExplorerResult`. Returned
observations and DataProfile candidates are not authoritative admission and do
not create Evidence.

See [Executor and dispatch](../../../docs/architecture/executor-and-dispatch.md)
for target authority and [Current state](../../../docs/status/current-state.md)
for the verified boundary and limitations.
