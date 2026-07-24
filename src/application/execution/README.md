# Application Execution Bounded Context (`application.execution`)

## 1. Purpose
`src/application/execution/` is the dedicated application bounded context for execution attempt admission, state transition protocol enforcement, executor dispatch, authoritative receipt intake, cancellation, and recovery.

## 2. Why the package exists
This package was established in Package S1-B to decouple execution attempt lifecycle and protocol mechanics from scientific governance, Discovery admission, and generic orchestrator clutter.

## 3. Owned authority
- Sole production writer for `ExecutionRunRecord`, `ExecutionOutboxRecord`, and `ExecutionInboxRecord` attempt transitions (`ExecutionAttemptTransitionService`).
- Reconstruction of durable `PreparedExecution` contracts and outbox dispatch (`dispatch_pending_attempts`).
- Ingestion of authoritative executor result receipts into fenced inbox rows (`submit_execution_result`).
- Attempt cancellation and technical retry authorization (`cancel_execution_attempt`, `authorize_retry`).
- Reconciliation of pending inbox rows and expired dispatch leases (`reconcile_execution_attempts`).

## 4. Forbidden responsibilities
- Direct modification or insertion of `AnalysisFrame`, `Evidence`, `Discovery`, or `SessionFrame` objects.
- Pydantic scientific evaluation or Hypothesis Analyst execution.
- Evaluation threshold checking or p-value interpretation.
- Direct raw SQL mutators outside `ExecutionAttemptTransitionService`.

## 5. Canonical inputs and outputs
- **Inputs**: Task UUID, Hypothesis UUID, method ID, parameter hash, `PreparedExecution` payload.
- **Outputs**: Durable `ExecutionRunRecord`, `ExecutionOutboxRecord`, fenced `ExecutionInboxRecord`, or technical failure receipts (`DataExplorerFailureResult`).

## 6. Happy path
1. Planner/application builds execution-admission operations (`build_execution_admission_operations`).
2. `ExecutionAttemptTransitionService.stage_admit_attempt` commits `ExecutionRun` (ADMITTED) and `ExecutionOutbox` (pending).
3. Worker claims outbox item -> status `DISPATCH_CLAIMED` / `dispatching`.
4. Dispatcher reconstructs `PreparedExecution` and invokes `DataExplorerDispatcherProtocol`.
5. Receiver canonicalizes `DataExplorerResult` digest into an `ExecutionInboxRecord` (pending).
6. Evidence admission recovery coordinator claims inbox for finalization.

## 7. Failure and recovery path
- If Data Explorer execution or dispatch throws an exception, dispatcher constructs a `DataExplorerFailureResult` and submits a `failed` inbox row.
- Expired leases are reclaimed by `reconcile_execution_attempts`.
- Interrupted or unfinalized inbox items are retried via `finalize_attempt`.

## 8. Transaction owner
`ExecutionAttemptTransitionService` is the sole transaction owner for all execution protocol records.

## 9. Retry / replay / fencing behavior
- Execution attempts use strict lease epochs and fencing tokens (`lease_epoch`, `dispatch_idempotency_key`, `finalization_fencing_epoch`).
- Authoritative result receipts require active lease matching; duplicate receipts replay idempotently, while conflicting receipts quarantine to `RESULT_CONFLICT`.
- Technical retries spawn direct successor `ExecutionRun` rows linked by `previous_attempt_id`.

## 10. Tests proving the boundary
- `tests/application/execution/test_transition_service.py`
- `tests/executor/test_registry_dispatcher.py`
- `tests/repositories/test_execution_race_conditions.py`
- `tests/repositories/test_execution_recovery_boundaries.py`
- `tests/architecture/test_architecture_enforcement.py`

## 11. Current limitations
- Deployment must supply an explicit worker loop to invoke `dispatch_pending_attempts` periodically.
- External executor side effects remain at-least-once.

## 12. Deferred work
- Further separation of outbox daemon worker infrastructure (S4).
