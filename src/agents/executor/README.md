# Executor package

The executor package is **Partially implemented** at generic dispatch plumbing
and **Unsupported** as a runnable canonical specialist workflow.

Current source provides a capability catalog, registry, selection helpers,
request validation, and a thin dispatcher. `graph_mining` and
`hypothesis_testing` wrappers register, but both default graph builders raise
`NotImplementedError`; `data_exploration` is catalogued without a registered
executor. Planner execution nodes do not use the dispatcher, and the shared
input/output contracts do not implement the canonical role-native contracts.

Catalog membership, wrapper registration, or a configuration entry does not
prove runnability. No fallback from an unavailable canonical specialist is
supported.

See [Executor and dispatch](../../../docs/architecture/executor-and-dispatch.md)
for target authority and [Current state](../../../docs/status/current-state.md)
for the verified current boundary.
