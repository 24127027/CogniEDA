# Data Explorer donor note

This historical package-local design is superseded by the canonical
[Executor and dispatch](../../../docs/architecture/executor-and-dispatch.md)
owner page. It is not architecture authority.

The current S0 implementation preserves only a bounded local donor path for
`DATA_ANALYSIS` and `DATA_PROFILING`, returning `DataExplorerResult`
observations or DataProfile candidates without creating Evidence.
`DATA_TRANSFORMATION` fails closed because successor dataset and DataProfile
semantics are not implemented. No returned draft is authoritative persistence.

See [Current state](../../../docs/status/current-state.md) for the verified
implementation boundary.
