# Identity, scope, and lineage

Research state is useful only when an identity continues to mean the same thing,
scope remains explicit, and every scientific claim can be traced through its
admitted lineage. CogniEDA therefore separates semantic identity from mutable
coordination metadata and separates historical truth from current authority.

## Stable identity and mutable metadata

An object's identifier is not permission to change its meaning. Changes to
Plan membership or dependencies, workflow scheduling, or presentation do not
redefine a `Task`; those properties belong to `Plan` or their separate owning
records.

A substantive change to the semantic work unit creates a successor Task rather
than mutating the existing identity in place. The old Task remains part of the
record. The successor makes the change explicit and allows downstream lineage
to keep referring to the meaning that was actually approved.

Plan follows a similar immutable-successor boundary. A bounded coordination or
planning-basis amendment creates a successor Plan. A sufficiently large change starts a new
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

Plan does not pre-bind that DataProfile. Planner expresses intended
data scope in Task semantics, and the responsible specialist or controller
selects concrete applicable profiles from the complete authoritative context
within its own authority. Actual execution and scientific provenance then bind
the exact profiles used. Concrete profile selection is therefore not existing
Plan content and does not, by itself, change its fingerprint.

Physical location does not establish dataset identity or admission. A
Workspace conventionally owns user-visible datasets under `data/`, but a
dataset may also remain at an explicitly admitted external path. In either
case, filesystem presence is not a DataProfile, and changed data requires a
successor physical dataset plus a successor DataProfile rather than an
in-place identity rewrite. See [Workspace ownership](../../development/workspace-layout.md).

## Objective scope and Hypothesis independence

Each Task and Plan is coordinated within one focal Objective. One Objective may
have many Tasks and many scientific investigations over time. A Workspace may
contain multiple active Objectives.

However, a `Hypothesis` represents an empirical scientific proposition whose
scientific identity and validity are independent of Objective ownership. A
Hypothesis contains no `objective_id`, `objective_ids`, or equivalent Objective
membership fields. Adding, removing, or changing a research Objective does not
mutate an existing Hypothesis or manufacture duplicate Hypotheses for the same
proposition.

In the future semantic Knowledge Graph, one Objective may associate with
multiple Hypotheses and one Hypothesis may be relevant to multiple Objectives.
Exact Objective-Hypothesis relation types, edge representation, persistence,
admission, and governance remain deferred until semantic graph implementation.

Objective relevance is research-intent/context semantics. It must not:
- alter Hypothesis scientific identity;
- alter Evidence or Discovery validity;
- imply that an Objective scientifically supports a Hypothesis;
- authorize unvetted cross-Objective Evidence reuse; or
- act as an automatic LLM similarity edge.

## High-level scientific lineage

The target conceptual graph separates scientific lineage from research-intent
relevance:

```text
                  Objective (research scope)
                      : (future graph association)
                      :
                  Hypothesis (scientific commitment)
                      |
          +-----------+-----------+
          |                       |
       Evidence                Discovery
```

The foundational lineage rules are:

```text
Objective
  -> many Tasks
  -> many scientific investigations over time

eligible feasible leaf SCIENTIFIC Task
  -> exactly one Hypothesis

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
Hypotheses, Evidence, Discoveries, or Plans.

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
