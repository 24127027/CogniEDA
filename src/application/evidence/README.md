# Evidence Application Package (`src/application/evidence/`)

> Canonical Documentation: [Execution to Evidence Workflow](../../docs/workflows/execution-to-evidence.md) | [Research State Model](../../docs/architecture/research-state-model.md)

## Purpose
Owns formal admission of observed empirical results into immutable `AnalysisFrame` and `Evidence` records.

## Owned Responsibilities
- `EvidenceAdmissionService` (`admission_service.py`).
- Creating immutable `AnalysisFrameRecord` and `EvidenceRecord` from Data Explorer observations.
- Updating target `TaskRecord` to `COMPLETED`.

## Forbidden Responsibilities
- Modifying `ExecutionRunRecord` leases (owned by `application.execution`).
- Evaluating scientific hypotheses (owned by Hypothesis Analyst).

## Canonical Inputs / Outputs
- Input: `DataExplorerResult` / `EvidenceObservation`, run ID, task ID.
- Output: `EvidenceAdmissionResult` (created `AnalysisFrame`, `Evidence`).

## Transaction Authority
Sole transaction owner for `AnalysisFrameRecord` and `EvidenceRecord` creation.

## Tests
- `tests/application/evidence/test_admission_service.py`
