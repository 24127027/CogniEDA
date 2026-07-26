# Validity Application Package

> **Role:** Package technical reference. **Canonical concept owner:**
> [Atomic validity propagation](../../../docs/concepts/validity/validity-propagation.md).
> **Contributor entry:** [Contributor documentation](../../../docs/development/index.md).
> **Current-state owner:** [CogniEDA current state](../../../docs/current-state.md).

Canonical references:
[Validity over time](../../../docs/concepts/validity/validity-over-time.md),
[Atomic validity propagation](../../../docs/concepts/validity/validity-propagation.md),
[Propagating validity changes atomically](../../../docs/design-decisions/propagating-validity-changes-atomically.md) and
[Validity propagation workflow](../../../docs/reference/workflows/validity-propagation.md).

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
