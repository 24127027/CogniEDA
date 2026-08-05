# Contract and cardinality reference

This is the concise lookup for scientific contracts, authority ownership,
cardinality, and fail-closed behavior. Use the
[scientific authority](../concepts/scientific-lifecycle/scientific-authority.md),
[Evidence and AnalysisFrames](../concepts/scientific-lifecycle/evidence-and-analysis-frames.md),
[protected evaluation](../concepts/scientific-lifecycle/protected-evaluation.md),
and [Discovery governance](../concepts/scientific-lifecycle/discovery-governance.md)
pages for explanation.

All entries describe **target design**. Exact field layouts are intentionally
not frozen here.

## Role-native boundary contracts

Unit B's specialist boundary remains unchanged:

```text
DataWorkOrder
  -> DataExplorerResult

ScientificInvestigationInput
  -> HypothesisAnalystResult

GraphInquiryRequest
  -> GraphInquiryResult
```

The contracts are intentionally distinct. A universal optional-field envelope
would create hidden authority channels. Unit C expands the scientific path
inside those boundaries without granting Data Explorer evaluation authority or
Hypothesis Analyst dataset access.

| Input or candidate | Output or transition | Scientific content owner | Admission or durable-transition owner | Fail-closed rule |
| --- | --- | --- | --- | --- |
| eligible leaf `SCIENTIFIC` Task | feasibility result | Hypothesis Analyst | application authority records exact result | reject wrong kind, parent, proposed/unapproved, wrong scope, or ineligible lifecycle |
| feasible scientific lineage | Hypothesis candidate | Hypothesis Analyst | application authority | reject missing contracts, lineage mismatch, duplicate Hypothesis, or invalid DataProfile binding |
| admitted Hypothesis | InvestigationPlan, InvestigationProtocol, Evidence obligations | Hypothesis Analyst | application authority | reject content authored by Planner or a structurally invalid candidate |
| Evidence obligation | EvidenceRequest | Hypothesis Analyst | application authority | reject generic prompt, wrong protocol revision, wrong scope, or missing obligation |
| admitted EvidenceRequest | DataWorkOrder | no new scientific content; application coordination performs exact projection | application authority coordinates dispatch | reject broadened or semantically altered derivation |
| DataWorkOrder | DataExplorerResult and EvidenceObservation candidate | Data Explorer owns bounded observation only | application authority validates result and provenance | reject unregistered capability, stale attempt, unauthorized operation, or result outside order |
| execution and observation lineage | Evidence candidate | no agent owns admission | application authority | reject missing or mismatched exact references/digests, invalid profile/protocol/obligation, or non-authoritative execution |
| eligible admitted lineage | EvaluationBundle | scientific authority consumes; application authority validates closure | application authority | exclude Assumptions, prior Discoveries, conversation, summaries, rejected Tasks, failed reasoning, unverified views, and unrelated Objectives |
| EvaluationBundle | typed outcome or DiscoveryProposal | Hypothesis Analyst or scientific investigation controller | application authority validates transition | reject open context, wrong decision rule, changed protocol, or ineligible Evidence |
| DiscoveryProposal | GovernanceDecision | governance decides without rewriting | application authority records exact decision | reject wrong proposal version, unauthorized reviewer, or ambiguous decision identity |
| approved exact proposal | Discovery | scientific content remains the proposal's content | application authority admits atomically | reject wrong outcome, lineage, Evidence eligibility, scope, validity basis, governance, or cardinality |

Agents propose or return bounded results. Application authority alone validates
and admits durable scientific transitions.

## Eight canonical scientific contract categories

For the current frozen architecture, C2 conceptually owns eight canonical
scientific contract schemas:

| Category | Semantic role | Cannot be inferred during canonicalization |
| --- | --- | --- |
| population or cohort | identifies the people, entities, events, or records to which the test applies | population membership or equivalence |
| variables | identifies the exact scientific variables and bindings | synonyms or fuzzy variable matches |
| measurement semantics and units | fixes what is measured and in which admitted units | unit conversion or semantic equivalence |
| DataProfile identity | binds the admitted immutable data state | nearest or latest profile selection |
| method and protocol | fixes method, parameters, decision rule, and procedural obligations | method compatibility or substitute test |
| uncertainty | fixes admitted uncertainty representation and treatment | missing uncertainty or confidence interpretation |
| limitations | fixes explicit constraints on interpretation | limitation meaning or waiver |
| claim scope | bounds what an eligible conclusion may assert | broader or implied claim scope |

Hypothesis Analyst may propose typed candidates. Application authority admits
immutable canonical records through deterministic typed validation, canonical
ordering, duplicate rejection, fixed serialization, schema-version binding,
and digest computation.

Canonicalization performs no synonym resolution, inferred unit conversion,
fuzzy mapping, population inference, method-compatibility inference,
limitation interpretation, claim-scope implication, or model, ontology, or
compatibility-registry call. Inputs not expressible in finite typed schemas are
rejected.

## Cardinalities

| Source | Target | Canonical cardinality | Consequence |
| --- | --- | --- | --- |
| eligible feasible leaf `SCIENTIFIC` Task | Hypothesis | zero or one; **at most one** | infeasible or terminated Tasks may have none |
| parent Task | Hypothesis | zero | parent Tasks cannot enter scientific commitment |
| parent Task | Discovery | zero | parent summaries are GeneratedViews, not Discoveries |
| ScientificInvestigationRun | EvidenceRequest | zero or many | multiple bounded observation rounds are allowed |
| EvidenceRequest | ExecutionRun | one or more attempts over time | retries are distinct traceable attempts |
| ScientificInvestigationRun | admitted Evidence | zero or many | each Evidence item satisfies a bounded obligation and lineage |
| Hypothesis | Discovery | zero or one; **at most one** | typed non-completion never manufactures a Discovery |
| Discovery | admitted Evidence | one or more references | Discovery cannot exist without eligible admitted Evidence |

## Exact-copy Evidence admission

Evidence admission exact-copies canonical references and digests from admitted
scientific lineage. It rejects missing references, mismatches, invalid
DataProfile binding, protocol mismatch, observation outside the obligation,
and non-authoritative execution lineage. It performs no semantic
canonicalization and never edits admitted Evidence in place.

## Authority exclusions

| Role | Must not do |
| --- | --- |
| Planner | author Hypothesis, scientific contract, protocol, obligation, decision rule, or protected evaluation |
| Hypothesis Analyst | access datasets, admit state, self-govern, or bypass Data Explorer |
| Data Explorer | evaluate Hypothesis, author DiscoveryProposal, govern, or admit Evidence |
| Graph Miner | mutate state, perform data execution, admit cross-Objective relations, or create Evidence/Discovery |
| governance | rewrite scientific content or perform durable admission |
| application authority | invent scientific meaning or governance judgment |

## Implementation status

**Design target.** Current source has partial legacy schemas and repository
guards but not these complete role-native contracts, canonical scientific
contract records, cardinalities, and fail-closed admissions as one supported
runtime path.
