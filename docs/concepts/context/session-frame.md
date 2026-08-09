# SessionFrame

`SessionFrame` is the First-Class Object for a governed active-context
selection. It makes a bounded working set durable and auditable across a
specific operation, handoff, pause, or resume without turning the selection
itself into scientific knowledge.

This page defines the **target design** for SessionFrame identity, scope,
lifecycle, and non-authority. Exact fields and storage layout remain unfrozen.

## Identity and binding

A canonical SessionFrame is bound to a specific:

- Objective;
- purpose;
- reasoning mode;
- scope;
- lifecycle point;
- validity basis.

It records selected references, explicit exclusions or restrictions needed for
the purpose, selection reasons, provenance, and the eligibility posture needed
to audit or reconstruct the frame. It is a governed selection, not a copied
knowledge base.

The identity must make it possible to distinguish a planning frame from a
protected-evaluation frame even when both refer to the same Objective. A change
of purpose, reasoning mode, scope, or relevant validity state may require a
new or successor frame rather than silent mutation of the earlier selection.

## FCO outside the semantic graph

SessionFrame is one of the eight FCOs, but it is not a semantic Knowledge Graph
node. The semantic graph remains exactly:

```text
Objective
Hypothesis
Evidence
Discovery
```

FCO identity lets a frame be addressed, governed, superseded, and recovered.
It does not grant scientific authority or semantic graph membership.

## What SessionFrame is not

SessionFrame is not:

- conversation history or raw chat turns;
- a chat or handoff summary treated as authority;
- a vector-search result;
- a GeneratedView;
- a semantic graph node;
- Evidence, Discovery, or scientific authority;
- universal memory or the full Workspace state;
- permission to ignore the selected objects' own lifecycle and validity.

A frame may carry bounded summaries for presentation or efficiency, but those
summaries do not replace the referenced authoritative records.

## Runtime Session and conversation

The bounded runtime keeps `SessionFrame` separate from interaction memory:

```text
Session
  -> SessionFrame
  -> ConversationHistory
```

`Session` is the in-process chat lifetime aggregate, not an FCO or scientific
authority. `ConversationHistory` is the ordered Human-to-Planner interaction
presented at that boundary. It is not embedded in `SessionFrame`, and provider
messages, tool protocols, retries, and intermediate model calls are not the
runtime conversation contract.

A Planner invocation builds purpose-specific initial context from the retained
frame and a normalized conversation projection. Conversation may resolve
discourse and references, but it cannot become Evidence or an empirical premise.
The evidence-grounded answer input remains restricted to admitted Evidence.

Initial invocation context is not a closed reasoning universe. An authorized
role may later acquire additional purpose-specific context during its run.
Information accessible during a run is not automatically selected into or
persisted in `SessionFrame`.

## Selection without authority transfer

Frame membership means only that a reference is selected for an authorized
purpose. Each selected record retains:

- its epistemic type;
- its original author and admission authority;
- its Objective and DataProfile scope;
- its scientific lineage;
- its lifecycle and current validity;
- its permitted uses and exclusions.

Selecting an Assumption into planning context does not promote it to Evidence.
Selecting a Discovery into answer context does not make it a premise for a new
protected evaluation. Selecting an execution result does not admit Evidence.

## Objective isolation

A SessionFrame remains Objective-scoped unless a specific authorized operation
explicitly permits otherwise. Related work from another Objective may be
presented as a suggestion to create or investigate a new Objective; it is not
silently imported as current authority.

Cross-Objective Evidence reuse requires explicit admission and exact equality
over the relevant versioned canonical typed obligations. A frame cannot prove
that equality merely by selecting two similar records.

## Lifecycle

A SessionFrame may conceptually be created, made active for its bound purpose,
checkpointed or handed off, reviewed after a validity change, superseded by a
new selection, and archived. These meanings do not freeze an enum.

Frame lifecycle must preserve:

- predecessor or successor identity where applicable;
- the purpose and mode for which the selection was valid;
- the exact authoritative references;
- warnings, blockers, exclusions, and pending review;
- why the frame stopped being current.

When a selected source becomes invalid, superseded, restricted, or stale, the
earlier frame remains truth-to-record. It must not continue as the active frame
for an affected use without review or reconstruction.

## Planner and application authority

Planner coordinates the desired active context for its Objective-scoped work.
Application authority validates eligibility, Objective binding, lifecycle,
validity, and permitted use before admitting the frame or its successor.

Neither boundary uses the frame to author scientific meaning. Protected
evaluation still requires its own closed EvaluationBundle and cannot consume a
raw SessionFrame as a substitute.

## Implementation status

**Partially implemented.** The active MVP `SessionFrame` is one frozen,
materialized-object schema with one optional Objective, ordered read-only
Assumption, Task, and Evidence collections, and one optional active DataProfile.
Validated successor seams preserve the fail-closed Task, Evidence, and
DataProfile invariants. A separate in-process runtime `Session` retains that
successor frame and normalized Human-to-Planner conversation across turns.

The active schema does not encode the complete canonical purpose, reasoning
mode, Objective-isolation, validity, or item-level eligibility model. Runtime
Session continuity is not restart-safe, and persisted snapshots are not composed
into durable resume or concurrency control. Therefore the bounded MVP surface is
not the complete canonical SessionFrame or continuity model.
