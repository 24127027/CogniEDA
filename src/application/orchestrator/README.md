# Orchestrator package

This package is **Partially implemented** and **Verified on SQLite** at narrow
application-authority boundaries:

- `planner_commit.py` applies supported approved PlannerOperation batches in a
  transaction;
- `execution_admission.py` builds a matched ExecutionRun/outbox proposal pair;
- `transition_service.py` owns attempt admission, dispatch leases, fencing,
  cancellation, and retry lineage.

There is no composed application orchestrator, request/response pipeline,
specialist result inbox, Evidence admission service, governance service,
validity orchestrator, or end-to-end recovery flow.

See [Persistence and admission](../../../docs/architecture/persistence-and-admission.md)
and [Current state](../../../docs/status/current-state.md).
