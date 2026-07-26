# SessionFrame and active context

CogniEDA preserves research state so an investigation can continue without
letting every stored object influence every later operation. A `SessionFrame`
is the user-governed projection that helps select a bounded active context. It
is not scientific authority.

> **Implementation status:** persisted SessionFrame snapshots, append/read
> access, bounded mode-specific projections, Planner successor frames,
> conclusion frames, and validity-driven frame supersession are
> **Implemented**. Their covered persistence behavior is **Verified on
> SQLite**. The item-governance experience is **Partially implemented**. A
> complete user-facing context editor and automatic workspace resume are
> **Unsupported**.

The project thesis remains:

> CogniEDA is validity-preserving research-state infrastructure.

That makes the priority order conclusion validity and traceability, context type
safety, then continuity. Remembering more is not allowed to reverse that order.

## Durable state is wider than active context

Durable research state is a historical record. It may retain completed Tasks,
evaluated Hypotheses, superseded Evidence, invalidated Discoveries, old
DataProfiles, rejected proposals, and superseded SessionFrames because later
review needs to know what happened.

Active reasoning context is narrower. A stored object does not gain authority
merely by being available. Context selection has to ask:

1. Is the object currently authoritative?
2. Is it an admissible epistemic type for this operation?
3. Does it belong to the relevant DataProfile and scope?
4. Is it relevant enough to fit the bounded context?

Authority and admissibility come before relevance. A retrieval score cannot
repair invalid lifecycle state, turn an Assumption into Evidence, or move a
Discovery silently from one dataset version to another.

The tempting alternative is to replay chat or inject every similar stored
summary. That is convenient, but it erases the difference between what a user
said, what the system planned, what an analysis observed, and what Evidence
actually supports.

## What SessionFrame represents

`SessionFrame` is a user-governed active-context projection. It can preserve a
compact snapshot of:

- the current Objective wording;
- selected DataProfile, Task, Assumption, Hypothesis, Discovery, and Evidence
  summaries and references;
- recent user-decision provenance;
- pending work, questions, warnings, stale markers, and dead ends;
- pins, exclusions, inclusion reasons, checkpoint or handoff metadata; and
- a link to a predecessor frame.

The frame carries summaries and references so a later operation can reconstruct
an appropriate projection. The underlying repositories remain authoritative
for current scientific and lifecycle state.

SessionFrame is not:

- long-term memory or raw chat history;
- the complete research graph;
- a scientific claim or an Evidence record;
- a retrieval index;
- a mutable narrative summary;
- an arbitrary prompt-context bag;
- a replacement for authoritative repositories; or
- the protected input used by the Hypothesis Analyst.

This separation protects the invariant that continuity must come from typed,
traceable state rather than persuasive prose.

## Logical user control and persisted snapshots

User governance is logical control over which otherwise admissible objects
remain prominent or excluded in ordinary planning. Persisted frame content is
append-oriented: ordinary changes create another snapshot rather than rewriting
the selected content of the earlier frame.

The current repository can create, read, list, and select the latest frame or
the latest frame whose status is active, checkpoint, or handoff. It exposes no
general update method. Planner Objective, root-Task, and decomposition paths can
stage a successor with a new identity and a predecessor reference in the same
approved operation batch.

An ordinary successor does not automatically mark its predecessor superseded.
Both snapshots may remain active-status records, while creation time determines
which one `get_latest` or `get_latest_active` returns. This is
**Partially implemented** current-cardinality behavior, not a claim that a
complete branch or session-selection policy exists.

Validity propagation is the deliberate exception to append-only selected
content. Its transaction may change lifecycle metadata on an affected frame to
superseded and append a stale marker. That removes the frame from
latest-active selection without deleting its historical snapshot. The
transaction and temporal-authority model are owned by
[Validity over time](validity-over-time.md) and
[Atomic validity propagation](atomic-validity-propagation.md).

## How frames are assembled today

The SessionFrame builder creates compact summaries with fixed per-type limits.
It preserves the order supplied by its caller and filters active Tasks,
Assumptions, Hypotheses, and user decisions for the categories it knows how to
summarize. It copies Discovery and Evidence lifecycle state so later context
projection can apply policy again.

The builder does not query repositories, rank candidates, infer scope
compatibility, or populate a complete explanation for every inclusion. Callers
choose and order the source objects. Pins and exclusions exist in the
SessionFrame contract, but there is no complete product surface for editing
them; current Discovery retrieval interprets them when a caller supplies a
frame.

Atomic Discovery admission builds a deterministic conclusion frame in the same
transaction that admits the Discovery and completes its scientific lifecycle
chain. That frame contains the admitted Discovery, supporting Evidence, current
DataProfile summary, Objective snapshot, and warnings. It contains no active
Assumptions. Generic repository and Planner writers reject a conclusion frame
that would bypass the admission owner.

The conclusion frame is a handoff artifact. It records what later work may
inspect; it did not author or justify the conclusion.

## Pins and exclusions

In current bounded Discovery retrieval:

- a valid Discovery pin adds strong structural priority and includes that
  Discovery in the candidate pool;
- an explicit exclusion removes the Discovery before scoring;
- exclusion wins if the same Discovery is both pinned and excluded;
- malformed or non-Discovery references are ignored with an exclusion note;
- a pin cannot restore an invalidated or deprecated Discovery;
- a pin cannot make a flagged or wrong-profile Discovery eligible to motivate
  a Task; and
- pins do not enter protected evaluation.

This is user control over context selection, not user power to redefine
scientific validity. A user may ask to keep an old claim visible for review.
They may not make its invalid Evidence current again by pinning its identifier.

### When a pinned Discovery later becomes invalid

Repository-backed retrieval re-reads the current Discovery, applies lifecycle
policy, and excludes an invalidated or deprecated record even when the pin
remains in a historical frame. The result carries a visible exclusion note for
the caller.

If a frame contains the affected Discovery, Evidence, Hypothesis, Task,
DataProfile, or corresponding summary/reference, validity propagation can mark
that frame superseded. A frame that contains only the Discovery identifier in
`user_pins` is not currently selected as an affected frame by that dependency
scan. It can therefore remain active-status with a historical pin, although the
pin still cannot reintroduce the invalid Discovery through current retrieval.

This scenario is classified **safe but under-enforced**: active scientific
authority is protected, while direct-reference stale marking is **Implemented**,
pin-only frame freshness is a **Known deviation**, and automatic successor
creation and user-facing notification are **Unsupported**. See
[Invalidation and active retrieval](invalidation-and-active-retrieval.md) for
the complete authority-versus-freshness review.

## One frame, several context modes

The current policy defines four mode names, but their support levels differ:

| Context | Current role | Status |
| --- | --- | --- |
| Planning Context | May project active workflow state, planning Assumptions, active or reviewable Discoveries, and current Evidence summaries | **Implemented** and used by current Planner Task paths |
| Answer Context | Projects current DataProfiles, active in-progress Hypotheses, active Discoveries, active Evidence, and warnings; excludes Assumptions and Tasks | helper **Implemented**; complete Planner answer path **Partially implemented** |
| generic Conclusion Context | Summary projection containing accepted current DataProfile, eligible Hypothesis, and active Evidence summaries | helper **Implemented** but not a protected scientific input |
| generic Discovery Synthesis Context | Same generic summary family under a scientific-sounding mode name | **Known deviation**; isolated from protected evaluation |
| Protected Conclusion Context | Closed repository-built bundle with complete authoritative lineage | **Implemented** separately; not SessionFrame-derived |

Only Planning Context has supported production `SessionContextBuilder` call
sites today. Answer, conclusion, and Discovery-synthesis projections are
exercised as policy helpers and tests; the answer Planner nodes remain
scaffold-level, and the generic scientific-sounding projections must never be
passed to the Hypothesis Analyst.

[Protected evaluation context](protected-evaluation-context.md) owns the closed
scientific boundary. It rebuilds canonical state from repositories and excludes
SessionFrames, pins, Assumptions, prior Discoveries, chat, and generic context
bags.

## Why snapshots instead of chat memory

Raw chat is attractive because it is already ordered and readable. It fails as
research continuity because corrections, rejected ideas, provisional beliefs,
and unsupported summaries remain equally fluent.

A typed frame makes selection inspectable and retains source references. The
cost is more explicit lifecycle policy, bounded projection logic, and successor
management. That cost is accepted because a later operation can explain which
typed objects were selected without treating the conversation as Evidence.

Append-oriented snapshots similarly cost storage and require a current-frame
selection policy. Destructive editing would be simpler, but it would erase what
an earlier operation was allowed to see. Revisit the snapshot design when
branching, multi-user governance, or frame volume requires explicit current
cardinality and concurrency rules; preserve historical traceability when doing
so.

## Current limitations and revisit triggers

- **Partially implemented:** there is no complete direct-manipulation UI for
  pins, exclusions, inclusion reasons, checkpoints, or handoffs.
- **Unsupported:** there is no automatic workspace-open bootstrap, restored
  chat conversation, or automatic project reopening.
- **Known deviation:** ordinary successor creation leaves earlier frames with
  their prior active-status metadata; recency chooses the latest snapshot.
- **Known deviation:** current frame lookup is workspace-database local, not
  filtered by user session, Objective, or branch.
- **Partially implemented:** a pin-only frame is not superseded by the current
  validity dependency scan, although retrieval still excludes invalid state.
- **Deferred:** persistent semantic indexing, Graph Miner, cross-project
  context, distributed retrieval, and multi-user context governance.

The design should be revisited when a frame becomes too large for direct
projection, reconstruction latency becomes material, several active
DataProfiles require explicit comparison, or users need explainable context
governance at product scale. Any replacement must keep invalid authority and
wrong epistemic types outside the operation before relevance is considered.

## Related decision rationale

Why user-governed active context remains separate from scientific authority is
summarized in
[Design decisions and tradeoffs](design-decisions-and-tradeoffs.md#17-user-governed-active-context).
The historical-retention consequences of stale frames are preserved in
[ADR-005](decisions/ADR-005-atomic-validity-propagation.md).

## Implementation orientation

The SessionFrame contract and persistence boundary are under
`src/schemas/research/session_frame.py` and
`src/repositories/research/session_frame.py`. Snapshot assembly and generic
projections are under `src/memory/`. Planner successor paths are under
`src/agents/planner/`; conclusion-frame creation is owned by
`src/application/discovery/`.

Focused verification is under `tests/memory/`, `tests/agents/planner/`,
`tests/application/`, and `tests/repositories/`.

Continue with
[Retrieval and context type safety](retrieval-and-context-type-safety.md), then
[Context reconstruction and continuity](context-reconstruction-and-continuity.md).
Selection, succession, checkpoint, and scaling limits are owned by
[SessionFrame scaling and resume boundary](session-frame-scaling-and-resume-boundary.md).
Validity-change consequences continue in
[Invalidation and active retrieval](invalidation-and-active-retrieval.md).
