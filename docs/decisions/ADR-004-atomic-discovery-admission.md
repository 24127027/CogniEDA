# ADR-004: Atomic Discovery Admission Transaction Ownership

**Status:** Accepted; implemented and verified on SQLite.

## Context

Split writers could leave a Discovery, lifecycle states, an admission claim, and
a governance decision inconsistent.

## Decision

`AtomicDiscoveryAdmissionService` is the sole supported Discovery
materialization transaction owner. `DiscoveryAdmissionCoordinator` is the
supported runtime entry point.

## Consequences

One transaction commits the exact proposal-copy Discovery, conclusion
SessionFrame, Task/Hypothesis/EvaluationControl transitions, committed admission
claim, and decision consumption. Public `DiscoveryRepository.create()` fails.

## Rejected alternatives

Public repository creation, Planner creation, and orchestrator-side inserts.

## Enforcement

`tests/architecture/test_architecture_enforcement.py` confines the writer and
`tests/application/discovery/test_atomic_discovery_admission.py` covers rollback,
replay, concurrency, governance, and exact-copy behavior. SQLite triggers fence
claim identity and exact decision consumption.
