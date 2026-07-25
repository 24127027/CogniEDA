# Execution Application Package (`src/application/execution/`)

> Canonical Documentation: [Execution to Evidence Workflow](../../docs/workflows/execution-to-evidence.md) | [Persistence and Transactions](../../docs/architecture/persistence-and-transactions.md)

## Purpose
Owns execution run dispatch, lease fencing, status transitions, and retry/recovery logic.

## Owned Responsibilities
- `ExecutionTransitionService` (`transition_service.py`).
- Managing `ExecutionRunRecord`, `ExecutionInboxRecord`, `ExecutionOutboxRecord`, and `ExecutionApprovalRecord`.
- Fenced lease acquisition, worker heartbeat, and attempt version incrementing.

## Forbidden Responsibilities
- Admitting `AnalysisFrame` or `Evidence` records (owned by `application.evidence`).
- Mutating scientific hypothesis claims.

## Canonical Inputs / Outputs
- Input: `PreparedExecution`, execution request token.
- Output: `ExecutionTransitionResult`, `ExecutionRunRecord`.

## Transaction Authority
Sole transaction owner for execution attempt records and inbox/outbox queues.

## Tests
- `tests/application/execution/test_transition_service.py`
