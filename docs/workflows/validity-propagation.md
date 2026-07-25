# Validity Propagation Workflow

> **Status**: `[Implemented]` / `[Verified on SQLite]`

This guide documents validity event creation, propagation through dependent research state, and active retrieval exclusion.

---

## 1. Workflow Summary

```text
Invalidation Command / Trigger Event
└──> AtomicValidityPropagationService
     ├──> Authority & Fingerprint Verification
     ├──> ValidityEventRecord Creation (Immutable)
     ├──> Dependent Target State Mutation (INVALIDATED)
     └──> Retrieval Index Exclusion Notification
```

---

## 2. Step-by-Step Specification

1. **Preconditions**: Invalidation request issued with valid authority token and target fingerprint.
2. **Inputs**: Source fingerprint, target ID, invalidation reason.
3. **Responsible Components**: `AtomicValidityPropagationService` (`src/application/validity/propagation_service.py`).
4. **Durable Writes**:
   - `ValidityEventRecord` (immutable audit record).
   - Target entity `validity_state` updated to `INVALIDATED` (`AnalysisFrameRecord`, `HypothesisRecord`, `DiscoveryAdmissionClaimRecord`).
5. **Retrieval Impact**: Invalidated entities remain in the SQLite database for historical traceability but are immediately excluded from active retrieval and conclusion contexts.
