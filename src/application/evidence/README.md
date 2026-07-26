# Evidence Application Package

> **Role:** Package technical reference. **Canonical concept owner:**
> [Scientific authority](../../../docs/concepts/scientific-lifecycle/scientific-authority.md).
> **Contributor entry:** [Contributor documentation](../../../docs/development/index.md).
> **Current-state owner:** [CogniEDA current state](../../../docs/current-state.md).

Canonical reference:
[Execution to Evidence](../../../docs/workflows/execution-to-evidence.md).

This package validates observation-only results, builds deterministic frozen
`EvidenceAdmissionPlan` values, and executes the sole supported AnalysisFrame
and Evidence admission transaction through `execute_evidence_admission_plan`.
The transaction also moves the fenced ExecutionRun to `EVIDENCE_ADMITTED`, the
Hypothesis to `READY_FOR_EVALUATION`, and consumes the authoritative inbox.

Evidence admission does not complete the Task, evaluate the Evidence, or create
a Discovery. Execution lease/queue transitions remain owned by
`ExecutionAttemptTransitionService`.

Primary verification:
`tests/application/evidence/test_evidence_admission.py`.
