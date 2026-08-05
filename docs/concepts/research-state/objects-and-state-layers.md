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
| `SessionFrame` | governed active context for a purpose and scope | no | not conversation history or generic memory summary |

No other record is an FCO. In particular, `Workspace`, `Question`,
`PlanRevision`, `InvestigationProtocol`, `AnalysisFrame`, `ExecutionRun`,
`GovernanceDecision`, `GeneratedView`, and cache records are not FCOs.

## Semantic graph membership

The semantic Knowledge Graph contains exactly:

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
planning constraints, workflow state, and active context have different
epistemic roles.

## Independent properties

Several properties that are often collapsed must be evaluated separately:

| Property | Question it answers | What it does not imply |
| --- | --- | --- |
| FCO status | Does this domain concept require durable first-class identity? | graph membership or scientific authority |
| semantic graph membership | Is this an epistemic research node in the canonical graph? | that all related state belongs in the graph |
| durability | Must the record survive sessions and restarts? | FCO status |
| immutability | May admitted content be rewritten? | graph membership |
| authority | Which boundary may propose, decide, admit, or transition it? | that the record is a scientific claim |

`Evidence` is an immutable FCO and graph node. `DataProfile` is an immutable FCO
outside the graph. `ExecutionRun` can be durable, transactionally important
provenance without being an FCO. `GovernanceDecision` can be authoritative for
admission without becoming scientific content.

## Major non-FCO state families

Non-FCO does not mean temporary, unimportant, or non-authoritative. It means the
record serves a planning, investigation, execution, provenance, evaluation,
governance, validity, presentation, or operational role rather than one of the
eight first-class domain identities.

| State family | Representative records | Responsibility |
| --- | --- | --- |
| planning and plan versioning | `PlanRevision`, `PlanTaskBinding`, `PlanTaskDependency`, `TaskLifecycleRecord`, `TaskPresentationMetadata`, `PlannerConsultationRun` | plan membership, dependencies, assignment, ordering, approval, and presentation |
| scientific investigation | `ScientificInvestigationRun`, feasibility record, `InvestigationPlan`, `InvestigationProtocol`, `ProtocolRevision`, `EvidenceRequest` | feasibility, operationalization, protocol evolution, and evidence obligations |
| execution and provenance | `ExecutionRun`, `AnalysisFrame` | attempt history and exact data-view lineage |
| evaluation and outcome | `EvaluationBundle`, `ScientificInvestigationOutcome`, `DiscoveryProposal` | protected inputs, typed endings, and proposed scientific content |
| governance and admission | `GovernanceDecision` and admission records | authorization and authoritative state transition |
| validity | validity events and review signals | historical trace and current-use eligibility |
| presentation | `GeneratedView` | derived answer, report, table, or synthesis without scientific authority |
| operational recovery | outbox, inbox, lease, fencing, recovery, and cache records | safe dispatch, retry, replay, and reuse |

This list is representative rather than exhaustive. Adding a durable record to
one of these families does not promote it to FCO or semantic-graph status.

## Generated views and active context

`GeneratedView` and `SessionFrame` solve different problems. A `GeneratedView`
is a derived presentation surface and can be regenerated when its sources or
validity change. It is neither an FCO nor authoritative scientific state.

`SessionFrame` is an FCO because a governed active-context selection must be
addressable across sessions. It still does not author a claim. The selected
objects retain the authority and eligibility rules of their own types.

## Where to go next

Read [Planning and scientific state](planning-and-scientific-state.md) for the
handoffs that prevent planning material from becoming scientific support.
Read the [Scientific lifecycle](../scientific-lifecycle/index.md) for the full
investigation and governance sequence.
Read [Identity, scope, and lineage](identity-scope-and-lineage.md) for successor
semantics and cardinalities. Use the
[object catalog](../../reference/object-catalog.md) for compact lookup.
