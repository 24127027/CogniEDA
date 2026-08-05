# Identity, scope, and lineage

Research state is useful only when an identity continues to mean the same thing,
scope remains explicit, and every scientific claim can be traced through its
admitted lineage. CogniEDA therefore separates semantic identity from mutable
coordination metadata and separates historical truth from current authority.

## Stable identity and mutable metadata

An object's identifier is not permission to change its meaning. Changes to
priority, ordering, assignment, dependencies, scheduling, or presentation do
not redefine a `Task`; those properties belong to `PlanRevision` and related
records.

A substantive change to the semantic work unit creates a successor Task rather
than mutating the existing identity in place. The old Task remains part of the
record. The successor makes the change explicit and allows downstream lineage
to keep referring to the meaning that was actually approved.

PlanRevision follows a similar version boundary. A bounded semantic amendment
creates a successor PlanRevision. A sufficiently large change starts a new
grounded planning loop rather than disguising a new plan as an edit to the old
one.

## DataProfile identity is immutable

A `DataProfile` is an authoritative immutable description of an admitted data
state. A file path alone is not data identity. If cleaning, filtering,
preprocessing, joining, or any other transformation changes the data state, the
result requires a new DataProfile. The earlier profile is not overwritten.

Scientific lineage and Evidence refer to the applicable DataProfile. This
allows a later validity review to determine which observations and claims
depend on a changed or invalidated data state.

## Objective scope

Each Task and scientific investigation is governed within one Objective. One
Objective may have many Tasks and many scientific investigations over time. A
Workspace may contain multiple active Objectives, but a Task or Hypothesis does
not acquire direct multi-Objective ownership.

Objective boundaries also constrain context and reuse. Work from another
Objective can motivate a proposal, but it does not automatically become
authoritative state in the new Objective.

## High-level scientific lineage

The foundational lineage is:

```text
Objective
  -> many Tasks
  -> many scientific investigations over time

eligible feasible leaf SCIENTIFIC Task
  -> at most one Hypothesis

Hypothesis
  -> admitted Evidence through investigation and provenance records
  -> at most one Discovery

parent Task
  -> no Hypothesis
  -> no Discovery
```

“At most one” is deliberate. A Task may be infeasible, never approved, or
cancelled. An investigation may fail, remain inconclusive without meeting the
valuable-inconclusive conditions, or end in another typed non-Discovery
outcome. None of those paths should create an object merely to satisfy an
exact-one count.

`AnalysisFrame` and `ExecutionRun` supply provenance without becoming FCOs.
`InvestigationPlan`, `InvestigationProtocol`, protocol revisions, and
`EvidenceRequest` records preserve scientific operationalization and evidence
obligations. `ScientificInvestigationOutcome`, `DiscoveryProposal`, governance,
and admission records preserve how an investigation ended and whether a claim
was authorized.

## Historical truth and current authority

Truth-to-record answers what was observed, proposed, admitted, or decided at a
particular time. Current authority answers whether that state is eligible for
protected use now. They are related but not identical.

If later review finds that a DataProfile, Evidence record, or claim is stale,
superseded, or invalid, CogniEDA preserves the historical record and changes
its current-use eligibility through governed lifecycle and validity state.
Invalidation is not deletion and not rewriting history.

The same principle applies to corrections. Wrong, stale, or superseded
analytical output requires new Evidence and a traceable relation to the old
record. The scientific content of admitted Evidence is not manually edited.

## Cross-Objective isolation

There is no generic cross-Objective relation admission in the canonical
architecture. Related prior work may motivate an inert proposal for a new
Objective, but it does not automatically aggregate or transfer Tasks,
Hypotheses, Evidence, Discoveries, or PlanRevisions.

Cross-Objective Evidence reuse requires explicit admission and exact equality
over the relevant versioned canonical typed obligations. Fuzzy similarity,
semantic resemblance, or natural-language equivalence is not sufficient.
Detailed admission predicates belong to a later contract reference; the
foundational rule is isolation unless exact typed obligations are satisfied and
reuse is explicitly admitted.

The [Contract and cardinality reference](../../reference/contract-and-cardinality-reference.md)
owns the current scientific contract and cardinality lookup.

## Structural canonicalization preserves meaning

Canonical construction makes structure deterministic. It may validate a finite
typed schema, order fields and sets canonically, reject duplicates, bind a
schema version, serialize fixed identifiers, enums, nulls, numbers, timestamps,
and text, and compute a digest.

It does not infer or rewrite semantic meaning. Structural canonicalization must
not resolve synonyms, infer unit conversions, map variables by similarity,
infer population equivalence, decide method or protocol compatibility,
interpret limitation prose, infer claim-scope containment, or call a model,
ontology, compatibility registry, or policy rule for semantic normalization.
Inputs that cannot be expressed in the finite typed schemas are rejected.

This distinction protects identity. Two meanings are not made equal merely
because a model considers them similar, and a digest does not certify semantic
equivalence that the typed contract did not express.

Read [Planning and scientific state](planning-and-scientific-state.md) for the
authority handoffs, use the [object catalog](../../reference/object-catalog.md)
for lookup, or return to the [research-state foundation](index.md).
