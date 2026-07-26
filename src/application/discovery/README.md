# Discovery Application Package

> **Role:** Package technical reference. **Canonical concept owner:**
> [Discovery governance and admission](../../../docs/concepts/scientific-lifecycle/discovery-governance-and-admission.md).
> **Contributor entry:** [Contributor documentation](../../../docs/development/index.md).
> **Current-state owner:** [CogniEDA current state](../../../docs/current-state.md).

Canonical references: [Creating Discoveries after authorization](../../../docs/design-decisions/creating-discoveries-after-authorization.md)
and [Evidence-to-Discovery workflow](../../../docs/reference/workflows/evidence-to-discovery.md).

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
