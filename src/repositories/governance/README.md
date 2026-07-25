# Proposal Decision Repository (`repositories.governance`)

## Purpose
`repositories.governance` owns persistence access for `ProposalDecisionRecord` and `GovernanceAuthorityRecord` entities.

## Modules
- `proposal_decision.py`: `ProposalDecisionRepository`.

## Responsibilities
- Lookup for proposal decisions by primary key, proposal digest, hypothesis, or decision fingerprint.
- Lookup for governance authority records by primary key.
- Staging and persisting decision records.
