# Proposal Decision Repository (`repositories.governance`)

> **Role:** Package technical reference. **Canonical concept owner:**
> [Governance and Discovery admission](../../../docs/governance-and-discovery-admission.md).
> **Contributor entry:** [Contributor documentation](../../../docs/development/index.md).
> **Current-state owner:** [CogniEDA current state](../../../docs/current-state.md).

## 1. Purpose

This package owns persistence access for `ProposalDecisionRecord` and
`GovernanceAuthorityRecord`.

## 2. Authority

`ProposalDecisionRepository` provides decision/authority lookups and private decision staging and
commit hooks for `DiscoveryAdmissionGovernanceService`.

## 3. Forbidden responsibilities

The repository does not issue authority, resolve principals, verify proposal lineage, classify
replay, consume decisions, create Discovery, or expose a public decision writer.

## 4. Inputs and outputs

Inputs are authority, decision, evaluation, proposal-digest, fingerprint, or Hypothesis identities.
Outputs are exact persisted rows or deterministic query lists.

## 5. Happy path

```text
governance service verifies principal/authority/proposal
  -> private repository create
  -> service-owned durable decision commit
```

## 6. Failure, retry, reclaim, and replay

The private create hook rolls back integrity races. The governance service reloads the winning row
and classifies exact replay versus conflict. Admission reclaim/consumption belongs to atomic
Discovery admission.

## 7. Transaction owner

`DiscoveryAdmissionGovernanceService` owns proposal-decision submission transactions.

## 8. Binding and fingerprints

Repository queries retain exact evaluation/proposal identity. Authority and decision fingerprint
calculation/verification remains in `application.governance`.

## 9. Tests

- `tests/repositories/governance/test_proposal_decision_races.py`
- `tests/application/governance/test_proposal_authorization.py`

## 10. Limitations

SQLite triggers/indexes provide the verified immutability and race boundary. The repository is not
an authentication or authorization adapter.
