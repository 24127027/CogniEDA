# Validity Application Package

Canonical references:
[ADR-005](../../../docs/decisions/ADR-005-atomic-validity-propagation.md) and
[Validity Propagation](../../../docs/workflows/validity-propagation.md).

`AtomicValidityPropagationService` verifies durable authority and source
fingerprints, derives a versioned plan, revalidates under the SQLite writer lock,
and atomically commits source/dependent state transitions plus one immutable
ValidityEvent.

The effect set can cover Evidence, EvaluationControl, admission claims,
Discovery, Hypothesis, Task review state, and SessionFrame supersession. No
retrieval-index notification exists; active retrieval excludes invalid state by
query policy.

Primary verification:
`tests/application/validity/test_validity_propagation.py`.
