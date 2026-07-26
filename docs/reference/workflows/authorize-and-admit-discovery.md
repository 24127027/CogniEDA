# Authorize and admit Discovery

> **Role:** Technical reference. **Canonical concept owner:**
> [Discovery governance and admission](../../concepts/scientific-lifecycle/discovery-governance-and-admission.md).
> **Contributor entry:** [Contributor documentation](../../development/index.md).
> **Current-state owner:** [CogniEDA current state](../../current-state.md).

> **Implementation status:** **Implemented** and **Verified on SQLite** for Discovery
> proposal decisions and admission authority.

The canonical reader explanation is
[Discovery governance and admission](../../concepts/scientific-lifecycle/discovery-governance-and-admission.md).
This page retains the source-oriented decision and consumption sequence.

## Authority and decision

`GovernanceAuthorityIssuer` in `src/application/governance/authority.py`
persists an expiring authority bound to the authenticated principal,
workspace/session, purpose, operation, issuer, and expiry. It does not create a
Discovery. The durable decision separately binds that authority to the exact
evaluation, proposal, bundle, Evidence set, Hypothesis, and Task.

`DiscoveryAdmissionGovernanceService` in
`src/application/governance/decision_service.py` validates that authority and
records one durable `ProposalDecision`. Supported outcomes are `APPROVED`,
`REJECTED`, and `CANCELLED`; there is no `MODIFY` outcome. A changed proposal
requires a new evaluated proposal and corresponding authority/decision.

```text
authenticated principal
  -> exact proposal-ready EvaluationControl
  -> authority issuance
  -> approved/rejected/cancelled ProposalDecision
  -> approved decision eligible for atomic Discovery admission
```

## Consumption boundary

Recording an approval does not materialize scientific truth. Only
`AtomicDiscoveryAdmissionService`, normally entered through
`DiscoveryAdmissionCoordinator`, may consume the exact approved decision while
committing the full Discovery chain.

SQLite triggers and service validation prevent:

- decision consumption without the matching committed admission claim;
- reuse across a different principal, action, resource, or proposal digest;
- silent mutation of immutable decision fields;
- split commits of Discovery, lifecycle changes, and decision consumption.

Rejected and cancelled decisions remain durable governance history and cannot be
used for admission.
