# Governance & Admission Workflow

> **Status**: `[Implemented]` / `[Verified on SQLite]`

This guide documents user authority token issuance, proposal decision recording, and fenced claim verification.

---

## 1. Workflow Summary

```text
DiscoveryProposal
└──> Governance Authority Generation (GovernanceAuthorityRecord)
     └──> User Decision (ACCEPT / REJECT / MODIFY)
          └──> ProposalDecisionRecord (consumed=0)
               └──> Fenced Admission Verification
                    └──> ProposalDecisionRecord (consumed=1)
```

---

## 2. Step-by-Step Specification

1. **Preconditions**: Evaluation control reaches `PROPOSAL_READY` state with a valid `DiscoveryProposal`.
2. **Inputs**: Proposal digest (`proposal_digest`), workspace ID, actor identity, user action.
3. **Responsible Components**: `ProposalDecisionService` (`src/application/governance/decision_service.py`), SQLite trigger guards.
4. **Durable Writes**:
   - `GovernanceAuthorityRecord` (immutable authority token).
   - `ProposalDecisionRecord` (immutable core decision details).
5. **Consumption Fencing**: SQLite trigger `proposal_decisions_exact_consumption` prevents `consumed` from mutating to `1` unless backed by an exact committed discovery admission claim chain in `discovery_admission_claims`.
