# ADR-005: Atomic Validity Propagation Transaction Ownership

**Status:** Accepted; implemented and verified on SQLite for the supported event
matrix.

## Context

Partial invalidation can leave dependent scientific state active after its
authority is lost.

## Decision

`AtomicValidityPropagationService` is the sole supported transaction owner for
validity source transitions, dependent effects, and immutable event insertion.

## Consequences

Authority and source fingerprints are verified while the deterministic
execution plan is built. Source and dependent writes then use compare-and-set
guards in the SQLite transaction. Exact replay requires the complete persisted
effect set; incompatible commands conflict. Validity has no separate
claim/lease/fencing protocol.

## Rejected alternatives

Deletion, repository-by-repository cascades, and asynchronous best-effort
retrieval notifications.

## Enforcement

`tests/application/validity/test_validity_propagation.py` covers atomic rollback,
authority, all supported source types, replay, races, and retrieval exclusion.
Dependency direction is checked by
`tests/architecture/test_architecture_enforcement.py`.

The current canonical explanation is
[Atomic validity propagation](../atomic-validity-propagation.md).
