# Application Evidence Bounded Context (`application.evidence`)

## 1. Purpose
`src/application/evidence/` is the dedicated application bounded context for Evidence admission plan validation and the atomic `AnalysisFrame` + `Evidence` write transaction.

## 2. Why the package exists
This package was established in Package S1-B to isolate pure deterministic Evidence plan validation (`admission_plan.py`) from the atomic database write transaction (`admission_service.py`) and ensure Evidence creation cannot be bypassed.

## 3. Owned authority
- Deterministic derivation of versioned `AnalysisFrame` and `Evidence` UUIDs (`generate_deterministic_analysis_frame_id`, `generate_deterministic_evidence_id`).
- Content fingerprinting for `AnalysisFrame` and `Evidence` (`compute_analysis_frame_fingerprint`, `compute_evidence_fingerprint`).
- Replay classification (`classify_evidence_admission_replay`).
- Validation of authoritative inbox observations against approved contracts (`validate_and_build_evidence_admission_plan`).
- Sole production authority for atomic `AnalysisFrameRecord` + `EvidenceRecord` insertion and attempt transition (`execute_evidence_admission_plan`).

## 4. Forbidden responsibilities
- Direct creation of `Discovery` or `DiscoveryProposal` objects.
- Hypothesis evaluation or claim synthesis (owned by Hypothesis Analyst).
- Direct modification of execution attempt protocol state outside `execute_evidence_admission_plan`.

## 5. Canonical inputs and outputs
- **Inputs**: Prepared execution contract (`PreparedExecution`), canonical observation envelope (`ExecutionReceiptEnvelope`), `ExecutionRunRecord`, `ExecutionInboxRecord`, `DataProfileRecord`, `HypothesisRecord`, `TaskRecord`.
- **Outputs**: Pure `EvidenceAdmissionPlan`, persisted `AnalysisFrameRecord`, persisted `EvidenceRecord`, Hypothesis status transition (`READY_FOR_EVALUATION`).

## 6. Happy path
1. Finalization recovery coordinator reads pending `ExecutionInboxRecord`.
2. Coordinator builds and validates `EvidenceAdmissionPlan` via `validate_and_build_evidence_admission_plan`.
3. Coordinator invokes `execute_evidence_admission_plan(session, plan)`.
4. Transaction stages `AnalysisFrame`, `Evidence`, updates `ExecutionRun` to `EVIDENCE_ADMITTED`, updates `Hypothesis` to `READY_FOR_EVALUATION`, and marks inbox `processed`.
5. Session commits atomically.

## 7. Failure and recovery path
- Inbox conflict or invalid payload causes `EvidenceAdmissionConflictError`, quarantining the attempt (`RESULT_CONFLICT`).
- Concurrent execution of identical plan returns `True` via idempotent replay check (`_committed_admission_matches`).

## 8. Transaction owner
`execute_evidence_admission_plan` in `admission_service.py` is the sole atomic transaction owner for AnalysisFrame and Evidence creation.

## 9. Retry / replay / fencing behavior
- Deterministic UUIDs prevent duplicate artifact creation for identical execution attempts.
- Replay classification evaluates exact fingerprint equivalence (`NEW`, `IDEMPOTENT`, `CONFLICT`).

## 10. Tests proving the boundary
- `tests/application/evidence/test_evidence_admission.py`
- `tests/repositories/test_execution_scientific_commit_races.py`
- `tests/architecture/test_architecture_enforcement.py`

## 11. Current limitations
- Currently invoked synchronously by reconciliation or recovery helpers.

## 12. Deferred work
- Event publishing for Evidence admission events (S4).
