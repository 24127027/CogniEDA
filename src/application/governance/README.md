# Governance Application Package (`src/application/governance/`)

> Canonical Documentation: [Governance and Admission Workflow](../../docs/workflows/governance-and-admission.md) | [Scientific Specialist Contracts](../../docs/architecture/scientific-specialist-contracts.md)

## Purpose
Owns user authority token generation and immutable proposal decision recording.

## Owned Responsibilities
- `ProposalDecisionService` (`decision_service.py`).
- Generating `GovernanceAuthorityRecord` tokens.
- Persisting `ProposalDecisionRecord` entries (user ACCEPT / REJECT decisions).

## Forbidden Responsibilities
- Authoring scientific proposals (owned by Analyst).
- Materializing `Discovery` objects (owned by `application.discovery`).

## Canonical Inputs / Outputs
- Input: `DiscoveryProposal`, user action token, actor identity.
- Output: `ProposalDecisionRecord`, `GovernanceAuthorityRecord`.

## Transaction Authority
Sole transaction owner for `GovernanceAuthorityRecord` and `ProposalDecisionRecord` creation.

## Tests
- `tests/application/governance/test_decision_service.py`
