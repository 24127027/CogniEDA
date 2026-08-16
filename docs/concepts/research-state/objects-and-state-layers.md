# Objects and state layers

CogniEDA gives First-Class Object status to domain concepts that need durable
identity and a first-class role in research state. This status is independent
of semantic Knowledge Graph membership, immutability, persistence mechanism,
or scientific authority.

## The eight First-Class Objects

There are exactly eight canonical First-Class Objects:

| First-Class Object | Research-state role | Semantic Knowledge Graph | Foundational boundary |
| --- | --- | ---: | --- |
| `Objective` | root research scope | yes | governs one investigation scope without becoming empirical support |
| `DataProfile` | authoritative description of an admitted data state | no | immutable; changed data state requires a new profile |
| `Assumption` | planning constraint | no | may guide planning; excluded from protected scientific evaluation |
| `Task` | durable semantic work unit | no | workflow identity; not scientific knowledge |
| `Hypothesis` | bounded scientific commitment | yes | created only for an eligible feasible leaf `SCIENTIFIC` Task |
| `Evidence` | admitted observation-backed scientific record | yes | immutable and bound to scientific lineage and provenance |
| `Discovery` | governed evidence-bound claim | yes | requires explicit claim, scope, validity basis, and admission |
| `SessionFrame` | structured research-session membership and active selectors | no | membership is not operation context, conversation memory, or scientific authority |

No other record is an FCO. In particular, `Workspace`, `Question`,
`Plan`, `InvestigationProtocol`, `AnalysisFrame`, `ExecutionRun`,
`GovernanceDecision`, `GeneratedView`, and cache records are not FCOs.

## Semantic graph membership

The semantic Knowledge Graph contains exactly four node types:

```text
Objective
Hypothesis
Evidence
Discovery
```

It contains epistemic research objects: the scope under investigation, the
scientific commitment, the admitted observation, and the governed claim. It is
not a universal persistence graph. `DataProfile`, `Assumption`, `Task`, and
`SessionFrame` remain FCOs outside the semantic graph because data state,
planning constraints, workflow state, and session membership have different
epistemic roles.

In the future semantic Knowledge Graph, one Objective may associate with
multiple Hypotheses and one Hypothesis may be relevant to multiple Objectives.
Hypothesis scientific identity remains Objective-independent (containing no
`objective_id` or `objective_ids` fields), and scientific validity flows
strictly through `Hypothesis -> Evidence -> Discovery`. Exact
Objective-Hypothesis relation types, edge representation, persistence,
admission, and governance remain deferred until semantic graph implementation.

## Independent properties

The five core properties are independent:

- **FCO status**: durable domain identity with first-class research-state role.
- **Semantic graph membership**: epistemic node (`Objective`, `Hypothesis`,
  `Evidence`, `Discovery`).
- **Durability**: persisted beyond process lifecycle.
- **Immutability**: payload cannot be rewritten in place.
- **Authority**: the role, component, or policy authorized to create or mutate
  the record.

| Object or record | FCO? | In semantic graph? | Durable? | Immutable payload? | Authority |
| --- | ---: | ---: | ---: | ---: | --- |
| `Objective` | yes | yes | yes | yes | Planner coordinates; application authority admits |
| `DataProfile` | yes | no | yes | yes | application authority admits |
| `Assumption` | yes | no | yes | yes | Planner coordinates; application authority admits |
| `Task` | yes | no | yes | status mutable; identity immutable | Planner proposes; application authority commits |
| `Hypothesis` | yes | yes | yes | yes | Hypothesis Analyst authors; application authority admits |
| `Evidence` | yes | yes | yes | yes | application authority admits |
| `Discovery` | yes | yes | yes | yes | governance authorizes; application authority admits |
| `SessionFrame` | yes | no | yes | active selectors mutable; history immutable | Planner coordinates; application authority persists |
| `Plan` | no | no | yes | yes | Planner proposes; human approves; application authority commits |
| `AnalysisFrame` | no | no | yes | yes | Data Explorer produces; application authority records |
| `ExecutionRun` | no | no | yes | attempt lifecycle mutable | application authority records |
| `DiscoveryProposal` | no | no | yes | yes | Hypothesis Analyst authors |
| `GovernanceDecision` | no | no | yes | yes | governance authorizes |
| `GeneratedView` | no | no | yes | regenerable | Planner coordinates |

An object may be an FCO without being in the semantic graph (`DataProfile`,
`Assumption`, `Task`, `SessionFrame`). An object may be in the semantic graph
without being user-editable (`Evidence`, `Discovery`). A record may be
authoritative for admission without becoming scientific content.

## Major non-FCO state families

Non-FCO does not mean temporary, unimportant, or non-authoritative. It means the
record serves a planning, investigation, execution, provenance, evaluation,
governance, validity, presentation, or operational role rather than one of the
eight first-class domain identities.

| State family | Representative records | Responsibility |
| --- | --- | --- |
| planning and Plan lifecycle | `Plan`, `PlanDependency`, `TaskLifecycleRecord`, `TaskPresentationMetadata`, `PlannerConsultationRun` | exact Objective and Assumption basis, direct Task-ID membership, explicit dependencies, approval, and presentation; execution strategy is excluded |
| scientific investigation | `ScientificInvestigationRun`, feasibility record, `InvestigationPlan`, `InvestigationProtocol`, `ProtocolRevision`, `EvidenceRequest` | feasibility, operationalization, protocol evolution, and evidence obligations |
| execution and provenance | `ExecutionRun`, `AnalysisFrame` | attempt history and exact data-view lineage |
| evaluation and outcome | `EvaluationBundle`, `ScientificInvestigationOutcome`, `DiscoveryProposal` | protected inputs, typed endings, and proposed scientific content |
| governance and admission | `GovernanceDecision` and admission records | authorization and authoritative state transition |
| validity | validity events and review signals | historical trace and current-use eligibility |
| presentation | `GeneratedView` | derived answer, report, table, or synthesis without scientific authority |
| operational recovery | outbox, inbox, lease, fencing, recovery, and cache records | safe dispatch, retry, replay, and reuse |

This list is representative rather than exhaustive. Adding a durable record to
one of these families does not promote it to FCO or semantic-graph status.

## Generated views and session membership

`GeneratedView` and `SessionFrame` solve different problems. A `GeneratedView`
is a derived presentation surface and can be regenerated when its sources or
validity change. It is neither an FCO nor authoritative scientific state.

`SessionFrame` is an FCO because structured session membership and active
selectors must remain addressable across interactions and restarts. It still
does not author a claim or replace operation-specific context construction.
Referenced objects retain the authority and eligibility rules of their own
types.

## Where to go next

Read [Planning and scientific state](planning-and-scientific-state.md) for the
handoffs that prevent planning material from becoming scientific support.
Read [Identity, scope, and lineage](identity-scope-and-lineage.md) for successor
semantics and cardinalities. Continue to the
[System overview](../../architecture/system-overview.md) before the
[Scientific lifecycle](../scientific-lifecycle/index.md). Use the
[object catalog](../../reference/object-catalog.md) for compact lookup.
