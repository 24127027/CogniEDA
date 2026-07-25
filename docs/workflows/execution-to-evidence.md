# Execution to Evidence Workflow

> **Status**: `[Implemented]` / `[Verified on SQLite]`

This guide documents execution attempt dispatch, Data Explorer observation, and atomic evidence admission.

---

## 1. Workflow Summary

```text
Analytical Task (READY)
└──> ExecutionTransitionService (dispatch)
     └──> Fenced ExecutionRunRecord (RUNNING)
          └──> Data Explorer Execution
               └──> AnalysisFrameObservation + EvidenceObservation
                    └──> EvidenceAdmissionService
                         ├──> AnalysisFrameRecord (Immutable)
                         ├──> EvidenceRecord (Immutable)
                         └──> TaskRecord (COMPLETED)
```

---

## 2. Step-by-Step Specification

1. **Preconditions**: Terminal analytical task in `READY` state with bound `Hypothesis` and execution contract.
2. **Inputs**: Execution contract, task parameters, random seed.
3. **Responsible Components**: `ExecutionTransitionService` (`src/application/execution/transition_service.py`), Data Explorer Agent (`src/agents/executor/data_explorer/agent.py`), `EvidenceAdmissionService` (`src/application/evidence/admission_service.py`).
4. **Durable Writes**:
   - `ExecutionRunRecord` lease acquisition and completion status.
   - `AnalysisFrameRecord` (provenance).
   - `EvidenceRecord` (observed result digest).
   - `TaskRecord` updated to `COMPLETED`.
5. **Failure / Retry**: If execution fails technically, `ExecutionTransitionService` handles retries or marks the run `FAILED`. If evidence admission fails validation, changes are rolled back atomically.
