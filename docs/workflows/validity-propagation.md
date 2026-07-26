# Validity Propagation Workflow

> **Implementation status:** **Implemented** and **Verified on SQLite** for the
> supported source/event matrix, exact replay, changed-command conflict,
> compare-and-set guards, and dependent-state propagation.

Canonical rationale and mechanics:
[Validity over time](../validity-over-time.md) and
[Atomic validity propagation](../atomic-validity-propagation.md). This page
retains the compact technical sequence.

## Atomic path

```text
authorized validity command
  -> AtomicValidityPropagationService
  -> validate authority, source type/state/fingerprint, event type, replacement
  -> derive versioned ValidityPropagationPlan
  -> apply source/dependent compare-and-set transitions in one SQLite transaction
  -> commit source/dependent transitions + immutable ValidityEvent
```

`src/application/validity/propagation_service.py` owns this path. Supported
events cover DataProfile invalidation/supersession, Evidence
invalidation/supersession/conflict, AnalysisFrame invalidity or provenance
corruption, and ExecutionRun conflict or provenance corruption. The plan
records stable fingerprints and the full intended effect set.

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
excluded by persisted lifecycle state and repository-backed retrieval policy;
they remain in SQLite for provenance and audit.

The active-context consequence is summarized in
[Retrieval and context type safety](../retrieval-and-context-type-safety.md) and
[Invalidation and active retrieval](../invalidation-and-active-retrieval.md).
