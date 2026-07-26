# Validity Application Package

Canonical references:
[Validity over time](../../../docs/validity-over-time.md),
[Atomic validity propagation](../../../docs/atomic-validity-propagation.md),
[ADR-005](../../../docs/decisions/ADR-005-atomic-validity-propagation.md) and
[Validity Propagation](../../../docs/workflows/validity-propagation.md).

`AtomicValidityPropagationService` verifies durable authority and source
fingerprints, derives a versioned plan, applies compare-and-set source and
dependent transitions, and atomically commits those transitions plus one
immutable ValidityEvent on the supported SQLite boundary.

The effect set can cover Evidence, EvaluationControl, admission claims,
Discovery, Hypothesis, Task review state, and SessionFrame supersession. No
retrieval-index notification exists; active retrieval excludes invalid state by
query policy.

Validity propagation has no separate claim, lease, or fencing-token protocol.

Primary verification:
`tests/application/validity/test_validity_propagation.py`.
