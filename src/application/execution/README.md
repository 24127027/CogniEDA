# Execution Application Package

Canonical references:
[Execution to Evidence](../../../docs/workflows/execution-to-evidence.md) and
[Persistence and Transactions](../../../docs/architecture/persistence-and-transactions.md).

`ExecutionAttemptTransitionService` owns durable run-attempt, dispatch outbox,
result inbox, lease/fencing, failure, retry, cancellation, and evidence-admission
transition stages. Dispatch/recovery coordinators call this service; external
effects remain at-least-once and are protected by identity, digest, owner,
epoch, and attempt-version checks.

This package does not author scientific claims and does not directly insert
AnalysisFrame, Evidence, or Discovery records.

Primary verification:
`tests/application/execution/test_transition_service.py` and
`tests/repositories/test_execution_recovery_boundaries.py`.
