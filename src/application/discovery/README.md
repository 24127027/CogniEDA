# Discovery Application Package

Canonical references: [ADR-004](../../../docs/decisions/ADR-004-atomic-discovery-admission.md)
and [Evidence to Discovery](../../../docs/workflows/evidence-to-discovery.md).

This package owns deterministic admission-plan construction, claim/replay
fencing, the supported coordinator, and the sole atomic Discovery transaction.
`AtomicDiscoveryAdmissionService` verifies authority under the SQLite writer
lock and commits the exact proposal-copy `Discovery`, conclusion
`SessionFrame`, terminal Task/Hypothesis transitions, committed evaluation and
claim state, and decision consumption.

It does not author proposals or make governance decisions. Public
`DiscoveryRepository.create()` is sealed.

Primary verification:
`tests/application/discovery/test_discovery_admission_plan.py` and
`tests/application/discovery/test_atomic_discovery_admission.py`.
