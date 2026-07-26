# Evidence-to-Discovery Workflow

> **Implementation status:** **Implemented** and **Verified on SQLite** for protected
> evaluation, governance, replay fencing, and atomic admission.

Canonical explanations:
[Protected evaluation context](../protected-evaluation-context.md),
[Governance and Discovery admission](../governance-and-discovery-admission.md),
and [From execution to Discovery](../from-execution-to-discovery.md). This page
retains the compact technical sequence.

## Protected evaluation

```text
Hypothesis(READY_FOR_EVALUATION) + active admitted Evidence
  -> EvaluationTransitionService claim
  -> build_synthesis_bundle reconstructs authority from repositories
  -> tool-free Hypothesis Analyst
  -> DiscoveryProposal or EvaluationFailure
  -> EvaluationControl(PROPOSAL_READY)
```

`DiscoverySynthesisBundle` is a frozen, closed schema. It contains the
Hypothesis, safe DataProfile metadata, AnalysisFrame/ExecutionRun provenance,
active Evidence, invalidators, method metadata, and a digest. It has no generic
context field and structurally excludes Assumptions, prior Discoveries,
SessionFrames, raw chat, raw data, files, and retrieval scores.

`EvaluationTransitionService` owns the durable evaluation-control lifecycle.
`src/agents/executor/hypothesis_analyst/agent.py` receives only the typed bundle,
has no tools, and returns a typed `DiscoveryProposal` or `EvaluationFailure`.

## Governance and atomic admission

```text
DiscoveryProposal
  -> GovernanceAuthorityIssuer issues expiring principal-bound authority
  -> DiscoveryAdmissionGovernanceService records exact proposal decision
  -> DiscoveryAdmissionCoordinator
  -> AtomicDiscoveryAdmissionService commits one transaction
       exact proposal-copy Discovery
       conclusion SessionFrame snapshot
       Hypothesis(EVALUATED)
       Task(COMPLETED)
       EvaluationControl(COMMITTED)
       DiscoveryAdmissionClaim(COMMITTED)
       ProposalDecision(consumed)
```

The admission service rebuilds and verifies authority under the SQLite writer
lock. The materialized `Discovery` must be an exact structural copy of the
authorized proposal. Exact replay is idempotent; a changed replay conflicts.

## Scientific meaning

`Evidence` is an immutable observation. `Discovery` is the authorized,
evidence-bound claim. Inconclusive and fail-to-reject results may still produce
knowledge, but must retain the method, scope, uncertainty, decision rule, and
validity basis that justify the limited claim.
