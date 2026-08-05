# Scientific lifecycle

CogniEDA treats scientific investigation as a governed lineage of distinct
records and authority transitions. It is not a shortcut from a Task to a tool
result and then to an insight.

This page and its child pages define the **target design**. They do not claim
that the complete lifecycle is implemented in the current runtime.

## Canonical lineage and authority sequence

```text
Objective
  -> PlanRevision
  -> Task
  -> ScientificInvestigationRun
  -> Hypothesis
  -> InvestigationPlan
  -> InvestigationProtocol
  -> EvidenceRequest
  -> ExecutionRun
  -> AnalysisFrame
  -> Evidence
  -> EvaluationBundle
  -> DiscoveryProposal
  -> GovernanceDecision
  -> Discovery
  -> GeneratedView
```

This is a lineage and authority sequence, not a promise that every
investigation reaches every stage. Feasibility may reject scientific
admission. Execution may be blocked. Evidence may be insufficient. Protected
evaluation may produce a typed non-Discovery ending. Governance may reject or
hold a proposal. No missing stage may be replaced with an untyped model answer.

The sequence must never be reduced to:

```text
Task -> tool call -> result -> insight
```

That reduction loses Task eligibility, scientific operationalization,
observation obligations, execution provenance, Evidence admission, protected
evaluation, governance, and authoritative Discovery admission.

## Stage map

| Stage | Epistemic or operational role | Governing authority |
| --- | --- | --- |
| `Objective` and `PlanRevision` | establish scope and an approved Task DAG | Planner proposes and coordinates; application authority admits and activates |
| eligible leaf `SCIENTIFIC` `Task` | identifies governed scientific work | Planner proposes work meaning; application authority enforces eligibility |
| `ScientificInvestigationRun` | binds the durable non-FCO investigation lifecycle | scientific authority proposes scientific transitions; application authority records them |
| `Hypothesis`, `InvestigationPlan`, `InvestigationProtocol`, and Evidence obligations | commit to what is tested and how | Hypothesis Analyst owns scientific content; application authority validates and admits |
| `EvidenceRequest` | requests one bounded observation obligation | Hypothesis Analyst authors; application authority admits and coordinates |
| `ExecutionRun`, `AnalysisFrame`, and observation candidate | record one attempt, exact analytical view, and returned observation | Data Explorer executes; application authority owns authoritative provenance transitions |
| `Evidence` | immutable admitted observation-backed scientific content | application authority admits; no agent admits Evidence |
| `EvaluationBundle` | closes the eligible scientific evaluation input | application authority constructs or validates eligibility; scientific authority evaluates |
| `DiscoveryProposal` | proposes an exact evidence-bound claim | protected scientific evaluation authors |
| `GovernanceDecision` | authorizes, rejects, holds, or redirects an exact proposal | governance |
| `Discovery` | records the admitted evidence-bound claim | application authority admits atomically |
| `GeneratedView` | presents eligible admitted state | Planner coordinates; it has no scientific authority |

## Cardinality and safe termination

An eligible feasible leaf `SCIENTIFIC` Task produces **at most one**
Hypothesis. A Hypothesis produces **at most one** Discovery. A parent Task
produces neither. These are upper bounds, not obligations to fabricate missing
scientific objects.

Typed non-completion may terminate the scientific investigation before
Discovery. The lifecycle preserves that outcome and its reason so the Planner
can present a blocker, request a correction, obtain additional grounding, or
propose replanning without weakening the scientific boundary.

## Read this section

- [Scientific authority](scientific-authority.md) owns initiation,
  feasibility, scientific contracts, protocols, and Evidence obligations.
- [Evidence and AnalysisFrames](evidence-and-analysis-frames.md) owns bounded
  observation requests, execution provenance, and Evidence admission.
- [Protected evaluation](protected-evaluation.md) owns the closed evaluation
  bundle, exclusions, decision-rule application, and typed outcomes.
- [Discovery governance](discovery-governance.md) owns proposal review,
  correction and additional-Evidence loops, and Discovery admission.
- [Lifecycle and outcome catalog](../../reference/lifecycle-and-outcome-catalog.md)
  is the concise stage and outcome lookup.
- [Contract and cardinality reference](../../reference/contract-and-cardinality-reference.md)
  is the concise authority, contract, cardinality, and fail-closed lookup.

## Implementation status

**Design target.** The lifecycle is not implemented end to end. Current source has FCO schemas,
minimal `ExecutionRun` and `AnalysisFrame` provenance, repository-level
Hypothesis/Evidence/Discovery guards, a generic dispatcher seam, and protected
context projection. It does not implement the canonical Task taxonomy,
`ScientificInvestigationRun`, the eight canonical scientific contracts,
role-native scientific execution, complete Evidence admission, an
`EvaluationBundle`, governance, or atomic Discovery admission through this
full sequence.
