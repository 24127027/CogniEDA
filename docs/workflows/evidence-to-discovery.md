# Evidence to Discovery Workflow

> **Status**: `[Implemented]` / `[Verified on SQLite]`

This guide documents protected hypothesis evaluation, scientific proposal authoring, governance decision, and atomic discovery materialization.

---

## 1. Workflow Summary

```text
Evidence-Ready Hypothesis
└──> EvaluationControlService
     └──> Protected Hypothesis Analyst Evaluation
          └──> DiscoverySynthesisBundle -> DiscoveryProposal
               └──> User Governance Decision (ProposalDecisionRecord)
                    └──> AtomicDiscoveryAdmissionService
                         ├──> DiscoveryRecord (Immutable)
                         ├──> DiscoveryAdmissionClaimRecord (COMMITTED)
                         └──> EvaluationControlRecord (COMMITTED)
```

---

## 2. Step-by-Step Specification

1. **Preconditions**: `Evidence` admitted for target `Hypothesis`.
2. **Inputs**: Protected Conclusion Context (Hypothesis, DataProfile, Evidence, parameters, decision rules; **Assumptions Quarantined**).
3. **Responsible Components**: Hypothesis Analyst Agent (`src/agents/executor/hypothesis_analyst/agent.py`), `EvaluationControlService` (`src/application/evaluation/control_service.py`), `ProposalDecisionService` (`src/application/governance/decision_service.py`), `AtomicDiscoveryAdmissionService` (`src/application/discovery/admission_service.py`).
4. **Durable Writes**:
   - `EvaluationControlRecord` state transitions (`PROPOSAL_READY` $\rightarrow$ `COMMITTED`).
   - `ProposalDecisionRecord` monotonic consumption (`consumed=1`).
   - `DiscoveryAdmissionClaimRecord` (`state='COMMITTED'`).
   - `DiscoveryRecord` (Immutable scientific claim).
5. **Exact Proposal-Copy Rule**: `AtomicDiscoveryAdmissionService` asserts that the materializing `Discovery` is an exact structural copy of the authorized `DiscoveryProposal`.
