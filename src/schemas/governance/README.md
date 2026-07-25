# Canonical Governance Schemas (`schemas.governance`)

## 1. Purpose

This package owns authenticated-principal, expiring authority, proposal-authority, and durable
decision value objects.

## 2. Authority

`authority.py` owns `AuthenticatedPrincipal`, `GovernanceAuthority`, and `ProposalAuthority`.
`decision.py` owns `GovernanceDecision`. These are the only canonical governance DTOs.

## 3. Forbidden responsibilities

The package does not persist grants/decisions, invoke the Analyst, create Discovery, import
application/repository code, or re-export contracts through the older Discovery-admission schema.

## 4. Inputs and outputs

Inputs are explicit identity, workspace/session, proposal-lineage, issuance, and decision fields.
Outputs are frozen `extra="forbid"` values; `GovernanceAuthority` requires an expiry.

## 5. Happy path

```text
AuthenticatedPrincipal -> GovernanceAuthority -> ProposalAuthority -> GovernanceDecision
```

## 6. Failure, retry, reclaim, and replay

Missing/extra/invalid fields fail model validation. Decision replay and expiry enforcement belong
to `application.governance`; schemas perform no retry or reclaim.

## 7. Transaction owner

None. Governance application services own durable writes.

## 8. Binding and fingerprints

These models carry exact binding inputs. Canonical authority, decision, and admission fingerprints
are computed by `application.governance.fingerprints`; the schema layer does not duplicate them.

## 9. Tests

- `tests/application/governance/test_proposal_authorization.py`
- `tests/repositories/governance/test_proposal_decision_races.py`
- `tests/architecture/test_architecture_enforcement.py`

## 10. Limitations

No authentication implementation or production issuer adapter is checked in. Persistence and
immutability guarantees are currently verified only for SQLite.
