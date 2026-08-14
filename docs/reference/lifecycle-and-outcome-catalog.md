# Lifecycle and outcome catalog

This page is a concise lookup for the canonical scientific lifecycle and its
outcomes. Explanations and rationale belong to the
[scientific lifecycle](../concepts/scientific-lifecycle/index.md) concept pages.

All entries describe **target design** unless explicitly labeled current.

## Canonical scientific sequence

```text
Objective
  -> Plan
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

The sequence expresses lineage and authority. It does not require every
investigation to reach every stage.

## Stage lookup

| Stage | Class | Created or controlled by | May terminate or branch before next stage? |
| --- | --- | --- | ---: |
| `Objective` | FCO; semantic graph | Planner coordinates; application authority admits | yes |
| `Plan` | non-FCO plan version | Planner proposes; human or policy approves; application authority activates | yes |
| `Task` | FCO workflow state | Planner proposes; application authority admits | yes |
| `ScientificInvestigationRun` | durable non-FCO lifecycle | scientific authority proposes transitions; application authority records | yes |
| `Hypothesis` | FCO; semantic graph | Hypothesis Analyst proposes; application authority admits | yes |
| `InvestigationPlan` | durable non-FCO scientific record | Hypothesis Analyst owns content; application authority admits | yes |
| `InvestigationProtocol` | durable non-FCO scientific record | Hypothesis Analyst owns content and revisions; application authority admits | yes |
| `EvidenceRequest` | durable non-FCO bounded request | Hypothesis Analyst authors; application authority admits and coordinates | yes; may repeat |
| `ExecutionRun` | durable non-FCO provenance | application authority admits attempt; Data Explorer executes | yes; retries create new attempts |
| `AnalysisFrame` | durable non-FCO provenance | Data Explorer returns view identity; application authority records | yes |
| `Evidence` | immutable FCO; semantic graph | application authority admits exact observation lineage | yes; may repeat |
| `EvaluationBundle` | durable non-FCO closed input | application authority validates eligibility; scientific authority evaluates | yes |
| `DiscoveryProposal` | durable non-FCO proposal | protected scientific evaluation | yes |
| `GovernanceDecision` | durable non-FCO authority record | governance | yes; may loop or terminate |
| `Discovery` | FCO; semantic graph | application authority atomically admits | no downstream scientific requirement |
| `GeneratedView` | non-FCO presentation | Planner coordinates from eligible state | regenerated or withheld as eligibility changes |

## Feasibility outcomes

| Outcome | Meaning | Hypothesis admitted? |
| --- | --- | ---: |
| feasible | eligible Task can be operationalized under typed scientific contracts | may be, after validation |
| not testable | no valid test contract can express the proposed work | no |
| insufficient data | required data state is absent or inadequate for admission | no |
| out of scope | proposed investigation exceeds Objective or approved Task scope | no |
| blocked by unavailable capability | required bounded scientific or data capability is unavailable | no |
| requires approval or additional grounding | consequential authority or grounding is missing | not until resolved |

## Discovery-eligible evaluation outcomes

| Outcome | Discovery eligibility |
| --- | --- |
| `SUPPORTED` | may produce an exact governed DiscoveryProposal |
| `CONTRADICTED` | may produce an exact governed DiscoveryProposal |
| `VALUABLE_INCONCLUSIVE` | only with completed protocol, clear value, narrow claim, proposal, governance, and admission |

Eligibility is not governance approval or Discovery admission.

## Representative non-Discovery endings

| Ending | Category | Result |
| --- | --- | --- |
| `NOT_TESTABLE` | feasibility or epistemic non-completion | no Discovery |
| `INSUFFICIENT_DATA` | data-grounding non-completion | no Discovery |
| `INSUFFICIENT_EVIDENCE` | epistemic non-completion | no Discovery |
| `PROTOCOL_EXHAUSTED` | protocol non-completion | no Discovery |
| `OUT_OF_SCOPE` | scope non-completion | no Discovery |
| `CANCELLED` | lifecycle termination | no Discovery |
| `INVALIDATED` | lifecycle or validity termination | no Discovery |
| `SUPERSEDED` | successor-lifecycle termination | no Discovery |
| `CANCELLED_BY_REPLAN` | plan-lifecycle termination | no Discovery |

Implementations may model epistemic outcome and lifecycle/termination reason as
separate types. They must not collapse a non-completion into a Discovery.

## Governance outcomes

| Decision | Consequence |
| --- | --- |
| approve | authorizes application authority to validate exact proposal admission |
| reject | proposal is not eligible for Discovery admission |
| hold | preserves exact pending identity without admission |
| request correction | returns content to scientific authority for a new traceable proposal version |
| request additional Evidence | returns through EvidenceRequest, execution, admission, and reevaluation |
| request conflict review | gathers eligible conflict information without rewriting scientific content |

## Implementation status

**Design target.** Current enums and repositories use legacy Task kinds and
outcome vocabularies and do not implement this complete catalog as one
end-to-end lifecycle.
