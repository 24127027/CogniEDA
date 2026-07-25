# Validity Propagation Workflow

> **Implementation status:** Implemented and verified on SQLite for the supported
> source/event matrix, exact replay, conflict fencing, and dependent-state
> propagation.

## Atomic path

```text
authorized validity command
  -> AtomicValidityPropagationService
  -> validate authority, source type/state/fingerprint, event type, replacement
  -> derive versioned ValidityPropagationPlan
  -> acquire SQLite writer lock and revalidate
  -> commit source/dependent transitions + immutable ValidityEvent
```

`src/application/validity/propagation_service.py` owns this path. Supported
events cover invalidation/supersession of `DataProfile`, `Evidence`,
`AnalysisFrame`, and `ExecutionRun`. The plan records stable fingerprints and
the full intended effect set.

Depending on the source and event, one transaction can update the source plus
affected Evidence, EvaluationControls, active admission claims, Discoveries,
Hypotheses, Tasks needing review, and SessionFrames that become superseded. It
then inserts the immutable `ValidityEvent`.

## Replay and failure semantics

- Exact replay succeeds only when all persisted effects still match.
- The same idempotency key with changed content conflicts.
- Concurrent exact commands produce one commit and one recognized replay.
- Concurrent incompatible commands produce one winner.
- Missing, stale, wrong-principal, or wrong-action authority fails closed.

There is no retrieval-index notification. Invalidated/deprecated Discoveries are
excluded by persisted lifecycle/validity state and query policy; they remain in
SQLite for provenance and audit.
