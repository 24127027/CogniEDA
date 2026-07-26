# Execution-to-Evidence Workflow

> **Role:** Technical reference. **Canonical concept owner:**
> [Execution to Discovery](../concepts/scientific-lifecycle/execution-to-discovery.md).
> **Contributor entry:** [Contributor documentation](../development/index.md).
> **Current-state owner:** [CogniEDA current state](../current-state.md).

> **Implementation status:** **Implemented** and **Verified on SQLite** for the
> library/runtime path. No production worker or concrete Data Explorer adapter is
> shipped.

The reader-first workflow is
[Execution to Discovery](../concepts/scientific-lifecycle/execution-to-discovery.md), and the
authority rationale is [Scientific authority](../concepts/scientific-lifecycle/scientific-authority.md).
The preceding approval boundary is
[Operation approval workflows](../operations/operation-approval-workflows.md).
This page retains the technical execution-to-Evidence sequence.

## Transaction sequence

```text
approved execution contract
  -> ExecutionAttemptTransitionService admits ExecutionRun + dispatch outbox
  -> dispatcher claims outbox with owner/epoch fencing
  -> configured DataExplorerAdapterProtocol implementation returns typed observations
  -> receiver persists authoritative inbox/result digest
  -> recovery finalizer builds EvidenceAdmissionPlan
  -> execute_evidence_admission_plan commits atomically
       AnalysisFrame
       Evidence
       ExecutionRun(EVIDENCE_ADMITTED)
       Hypothesis(READY_FOR_EVALUATION)
       inbox consumption
```

`ExecutionAttemptTransitionService` in
`src/application/execution/transition_service.py` owns run, outbox, inbox,
lease, fencing, and retry transitions. Dispatch uses the private
`DataExplorerRegistry`/dispatcher boundary; the adapter observes and returns
typed results but does not write research state or evaluate a hypothesis.

`execute_evidence_admission_plan` in
`src/application/evidence/admission_service.py` is the sole supported atomic
AnalysisFrame/Evidence admission path. Exact concurrent replays recognize the
committed winner; incompatible artifact identities are quarantined as conflicts.

## State and failure rules

- An outbox row is dispatch intent; an inbox row is received executor output.
- Technical failure is represented on `ExecutionRun`; it does not manufacture
  Evidence.
- Lease owner, fencing epoch, attempt version, dispatch idempotency key, and
  result digest are revalidated before admission.
- Evidence admission does **not** complete the Task. The Task remains active
  until authorized Discovery admission commits the scientific chain.
- `AnalysisFrame` is provenance, and `ExecutionRun` is workflow provenance;
  neither is an FCO.

## Not yet implemented

The runtime requires one injected Data Explorer adapter factory and context
factory. The repository contains no production adapter, process worker, daemon,
or service bootstrap.
