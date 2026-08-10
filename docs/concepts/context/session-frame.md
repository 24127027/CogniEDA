# SessionFrame

`SessionFrame` is the First-Class Object for cumulative structured
FCO-reference history within a session, plus explicit active selectors. It
preserves what genuinely entered that session's research history without
turning membership or current activity into scientific authority.

This page defines the **target design** for SessionFrame identity, scope,
lifecycle, and non-authority. Exact fields and storage layout remain unfrozen.

## Identity and binding

A canonical SessionFrame is bound to a session and preserves historical
membership separately from active selection. A complete target frame also
binds the applicable:

- Objective;
- purpose;
- reasoning mode;
- scope;
- lifecycle point;
- validity basis.

It records cumulative references and explicit active selectors, plus the
exclusions, restrictions, provenance, and eligibility posture needed to audit
or reconstruct context. Historical membership, active selection, and the
bounded subset selected for one Planner run are distinct.

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
  +-- SessionFrame
  |   +-- cumulative FCO references
  |   `-- active selectors
  `-- ConversationHistory
      `-- ConversationTurn
          +-- Human/Planner surface interaction
          `-- ConversationSegment[]
              `-- native ModelMessage[]
```

`Session` is the in-process chat lifetime aggregate, not an FCO or scientific
authority. `ConversationHistory` retains the complete Human-to-Planner surface
transcript separately from native model interaction. Each
`ConversationSegment` is one indivisible native PydanticAI `ModelMessage` unit,
so context pruning cannot split coherent tool-call/tool-return protocol.
Deterministic turns may contain no segment; the runtime does not fabricate
model messages for them.

A Planner invocation first selects a bounded set of historical FCO references,
surface discourse turns, and whole conversation segments. Surface discourse is
passed through an explicitly non-authoritative typed field for intent and
reference resolution; only native segment messages enter PydanticAI
`message_history`. `BuildPlanningContext` then resolves FCO references through
authoritative repositories, expands required Evidence Task and DataProfile
dependencies, validates lineage needed for safe use, and materializes the
ephemeral run context. Dependency resolution does not add SessionFrame
membership. Conversation cannot become Evidence or an empirical premise.

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

An active SessionFrame run selection remains Objective-scoped unless a specific
authorized operation explicitly permits otherwise. Cumulative history may
retain prior Objective IDs; inactive membership does not silently enter current
authority. Related work from another Objective may be presented as a suggestion
to create or investigate a new Objective.

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

**Partially implemented.** The active MVP `SessionFrame` is one frozen typed
reference manifest with cumulative ordered Objective, Assumption, Task,
DataProfile, and Evidence IDs plus `active_objective_id` and
`active_data_profile_id`. Active selectors must reference historical members;
duplicate historical IDs fail validation. Successors retain prior membership
when an active Objective or DataProfile changes. The frame stores no
materialized objects and imports no PydanticAI types.

The bounded `PlannerContextSelector` selects the active Objective and
DataProfile plus the 20 most recent Assumption, Task, and Evidence candidates.
Conversation selection separately chooses surface turns and whole native
segments by four-turn recency plus exact lexical overlap after deterministic
NFKC normalization, case folding, and Unicode-aware word extraction.
`BuildPlanningContext` resolves only the bounded FCO selection and expands a
selected Evidence item's authoritative Task and DataProfile even when those
dependency IDs were not directly selected. Missing dependencies and
non-`COMPLETED` Evidence Tasks fail closed. Historical Evidence for another
DataProfile remains stored but is not materialized into an active-profile run.

A separate in-process runtime `Session` retains the successor frame and the
complete `ConversationHistory`. Surface Human/Planner text and native model
segments are both retained without semantic duplication. Request understanding
receives selected surface discourse through its non-authoritative typed input
and selected whole-segment native history through PydanticAI's
`message_history` channel; empirical answer composition still excludes
conversation and Assumptions. `STATE_SUMMARY` uses cumulative SessionFrame
membership for historical counts and the authoritatively resolved active
Objective for its descriptive text; bounded `PlanningContext` counts are not
presented as whole-session totals.

The active schema does not encode the complete canonical purpose, reasoning
mode, Objective-isolation, validity, or item-level eligibility model. Runtime
Session continuity is not restart-safe, and persisted snapshots are not composed
into durable resume or concurrency control. Therefore the bounded MVP surface is
not the complete canonical SessionFrame or continuity model.
