# Research-state foundation

Research state is the governed, durable account of an investigation: its
scope, planned work, admitted data state, scientific commitments, observations,
outcomes, authority decisions, validity, provenance, and active context. It is
not a transcript and not a collection of semantically similar text.

The distinction matters because continuity requires more than recalling what
was discussed. A later session must be able to reconstruct what remains in
scope, which statements are provisional, what was observed, which claims were
admitted, and what is still eligible for current use.

## A layered mental model

CogniEDA separates research state into conceptual layers. These layers describe
responsibilities; they do not prescribe packages, databases, or deployment
boundaries.

```text
Research scope and planning
  Objective, Assumption, Task, PlanRevision
                 |
                 v
Scientific commitments and epistemic objects
  Hypothesis, Evidence, Discovery
                 ^
                 |
Execution and provenance
  InvestigationProtocol, EvidenceRequest, AnalysisFrame, ExecutionRun
                 |
                 v
Evaluation and governance
  ScientificInvestigationOutcome, DiscoveryProposal, GovernanceDecision,
  authoritative admission
                 |
                 v
Validity and eligibility
  historical record, validity events, current-use rules
                 |
                 v
Active context and generated views
  SessionFrame, bounded projections, GeneratedView
```

The arrows show governed handoffs, not automatic promotion. A plan does not
become Evidence. An execution result does not authorize its own interpretation.
A proposal does not become a Discovery until the required governance and
application admission occur. A generated answer remains presentation rather
than scientific authority.

## Which state is epistemic?

The semantic Knowledge Graph contains exactly four object types:

```text
Objective
Hypothesis
Evidence
Discovery
```

These objects express research scope, scientific commitment, admitted
observation, and evidence-bound claim. The graph does not contain every durable
record. `DataProfile`, `Assumption`, `Task`, and `SessionFrame` are First-Class
Objects but are not semantic Knowledge Graph nodes. Planning, execution,
provenance, governance, validity, recovery, and presentation records remain in
their own state layers.

This separation prevents two common errors. First, durable identity does not
grant scientific authority. Second, persistence does not imply semantic graph
membership. A `Task` must survive sessions, but it is still workflow state. An
`ExecutionRun` may be essential and immutable provenance without being an FCO
or a scientific claim.

## How layers interact

Planning starts within an `Objective`. It may use `Assumption` objects to decide
what to investigate and uses `PlanRevision` records to express an approved or
proposed Task graph. Those planning materials cannot silently become support
for a claim.

An eligible feasible leaf `SCIENTIFIC` Task may enter a scientific
investigation. The Hypothesis Analyst owns feasibility and scientific
operationalization. Bounded data work can produce observations and provenance;
application authority decides whether they satisfy the admission contract for
`Evidence`.

Protected evaluation is constructed from the `Hypothesis`, admitted
`DataProfile`, `AnalysisFrame` provenance, admitted `Evidence`, method metadata,
parameters, decision rule, uncertainty, validity basis, and necessary
provenance. It excludes `Assumption` objects and prior `Discovery` objects. The
result may be a `DiscoveryProposal` or a typed non-completion. Governance may
approve, reject, or hold an eligible proposal, but it does not rewrite the
scientific content. Application authority admits only the authorized resulting
state.

Validity then controls current eligibility without erasing the historical
record. A later `SessionFrame` selects a bounded context for a particular
purpose and scope. A `GeneratedView` may present current valid state, but the
view does not become authoritative scientific state.

## Continuity without category collapse

A useful resumed context is smaller than the full project history and richer
than a summary. It preserves identifiers, types, scope, lineage, lifecycle, and
validity while excluding material that is unsafe for the current purpose.

This is why CogniEDA can preserve both of these statements at once:

- an earlier result remains true-to-record as an account of what was observed
  and admitted at the time;
- that result is no longer eligible as current scientific authority after a
  relevant validity change.

The system does not need to rewrite history to protect present reasoning.

## Continue reading

1. [Objects and state layers](objects-and-state-layers.md) classifies the eight
   FCOs and the major non-FCO record families.
2. [Planning and scientific state](planning-and-scientific-state.md) explains
   why planning authority cannot become scientific authority.
3. [Scientific lifecycle](../scientific-lifecycle/index.md) defines the
   investigation, Evidence, evaluation, outcome, and governance sequence.
4. [Identity, scope, and lineage](identity-scope-and-lineage.md) explains
   successor identity, cardinality, historical authority, and cross-Objective
   isolation.

For lookup, use the [object catalog](../../reference/object-catalog.md) and
[terminology reference](../../reference/terminology.md). For the motivating
failure modes, read [Problem and thesis](../../problem-and-thesis.md).
