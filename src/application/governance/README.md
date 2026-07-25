# Governance Application Package

Canonical reference:
[Governance and Admission](../../../docs/workflows/governance-and-admission.md).

`GovernanceAuthorityIssuer` persists expiring authority bound to the resolved
principal, action, resource, workspace/session, and proposal identity.
`DiscoveryAdmissionGovernanceService` verifies that authority and records an
exact `APPROVED`, `REJECTED`, or `CANCELLED` proposal decision.

Governance neither authors the proposal nor materializes a Discovery. Decision
consumption belongs to the atomic Discovery transaction.

Primary verification:
`tests/application/governance/test_proposal_authorization.py` and governance
cases in
`tests/application/discovery/test_atomic_discovery_admission.py`.
