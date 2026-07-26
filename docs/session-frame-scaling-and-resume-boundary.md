# SessionFrame scaling and resume boundary

A `SessionFrame` is an append-oriented projection of active research context.
It helps a user or Planner reconstruct what should be visible next; it is not a
database session, a chat transcript, a scientific premise, or a durable process
checkpoint.

> **Implementation status:** Typed frames, append-oriented persistence,
> explicit predecessor metadata, bounded context projection, pins, exclusions,
> and validity-driven frame supersession are **Implemented**. Frame selection,
> product UI, and end-to-end process resume are **Partially implemented**.
> Fully user-, session-, Objective-, and branch-scoped continuity is a **Design
> target**.

[SessionFrame and active context](session-frame-and-active-context.md) owns the
frame's epistemic role and user-governance rules. This page owns selection,
succession, checkpoint, resume, freshness, and scaling limits.

## What is durable today

The repository supports create, get, list, recent, latest, and latest-active
reads. Creation appends a new frame identity; there is no general in-place
update path. A frame can contain:

- an objective snapshot;
- active profile references;
- relevant Task, Assumption, Hypothesis, Discovery, and Evidence references;
- pending work and recent decisions;
- user pins and exclusions;
- warnings and stale markers;
- a predecessor frame identity;
- branch and checkpoint labels; and
- handoff metadata.

The context builder produces bounded typed projections. Current defaults cap
profiles, Tasks, Assumptions, Hypotheses, Discoveries, Evidence, and decisions,
and preserve the caller's ordering. It does not silently refresh every object
from repositories while building the projection.

Scientific finalization can append a deterministic conclusion frame in the same
transaction as Discovery admission. That frame records the authoritative
profile, Evidence, Discovery, and warnings for the conclusion; it does not
admit Assumptions into protected synthesis.

## Selection is currently database-global

`get_latest_active` treats `ACTIVE`, `CHECKPOINT`, and `HANDOFF` as selectable
and orders by creation time descending. It does not filter by user, Planner
session, Objective, workspace branch, or device, and it has no deterministic
tie breaker beyond the stored timestamp.

The schema has branch, checkpoint, and handoff metadata, but no durable
`session_id`, `user_id`, or `objective_id` field. The objective is a text
snapshot rather than an identity-scoped selector. No database constraint
enforces one active frame for a logical thread.

Planner request grounding is safer when an exact `session_frame_id` is supplied:
root Task and decomposition paths read that frame by identity. Objective
management, however, currently reads database-global `get_latest`, not
`get_latest_active`. A newer superseded or archived frame can therefore be used
as the source for a proposed successor. That is a continuity **Known
deviation**, not a scientific-authority bypass.

## Snapshot succession

Ordinary Planner paths create a new UUID and set
`parent_session_frame_id` to the source frame. This provides history and makes a
transition auditable without rewriting the predecessor. The old frame commonly
remains active, so “latest” is an implicit recency convention rather than an
enforced single-head branch.

Snapshot succession provides:

- immutable historical views of active context;
- simple comparison and audit;
- explicit predecessor, checkpoint, branch, and handoff metadata; and
- an append-friendly recovery artifact.

It also costs growing storage, repeated references and summaries, cleanup and
compaction policy, and ambiguous head selection when multiple actors or
branches create frames concurrently.

The mechanism is a Durable operational boundary for the current local model,
not a claim that creation-time ordering is the permanent branch design.

## Freshness after validity changes

Validity propagation can supersede affected active frames and append a stale
marker. Repository-current retrieval independently re-reads referenced
Discoveries and excludes invalidated or deprecated authority.

One **Known deviation** remains: dependency discovery does not treat a
Discovery named only in `user_pins` as a frame dependency. Such a frame may
remain `ACTIVE` without a stale marker after that Discovery is invalidated.
Retrieval still fails safely because the pin cannot restore lifecycle authority,
but the frame's displayed freshness can be misleading until reconstructed.

This distinction matters:

- current scientific authority comes from repository-current objects and
  context policy;
- SessionFrame freshness communicates whether the stored projection should be
  rebuilt; and
- a stale or missed stale marker must never make invalid authority admissible.

## Checkpoint and resume seams

Several mechanisms are easy to confuse:

| Seam | Durable across process restart? | What it restores |
| --- | --- | --- |
| `SessionFrame` | yes | a bounded research-context projection |
| `PlannerOperation` proposal | yes | exact pending ordinary operations and approval state |
| `ExecutionApproval` | yes | one exact prepared execution contract and decision state |
| execution run, outbox, and inbox | yes | dispatch, receipt, and reconciliation state |
| LangGraph default `MemorySaver` | no | in-process graph checkpoint state only |
| raw chat or arbitrary node progress | no | not restored by the supported runtime |

Planner execution reconciles durable attempts when a configured run begins, and
the runtime exposes explicit reconciliation. Exact operation or execution
approval IDs can reconstruct their narrow durable workflow state.

That is not complete restart-safe product continuity. The caller must still
know which frame or approval to resume; arbitrary graph messages and node
position are not durably restored; pending result and conflict review are not
durable product interactions; and no worker loop or product bootstrap
coordinates recovery after a process stops.

The in-memory checkpointer is a **Current-stage implementation choice**. It must
not be described as durable LangGraph process checkpointing.

## User governance is not yet a product UI

Pins, exclusions, warnings, inclusion reasons, stale markers, checkpoints, and
handoff fields are useful typed seams. They do not prove that a user can inspect
and edit them through a supported interface.

The current product lacks:

- an interactive active-context editor;
- user- and Objective-scoped frame discovery;
- branch-head selection and merge;
- conflict handling for concurrent frame creation;
- cross-device session discovery;
- a review flow for stale pins or invalidated references; and
- a complete “resume where I stopped” experience.

The user-governance model is therefore **Partially implemented**. Any UI must
keep inclusion and exclusion visible and must not let a pin override current
scientific validity.

## Current operating assumption

The database-global convention is acceptable only under a narrow local
assumption: one workspace database, one active operational thread, in-process
coordination, and an explicit frame identity on the paths that require precise
context.

It does not scale safely to multiple simultaneous Objectives, concurrent
Planner sessions, multiple users, cross-device work, branch merge, or frequent
large-frame edits. Those cases need explicit ownership and selection semantics
before “latest” can be treated as meaningful.

## Scaling and revisit triggers

Revisit the frame model when:

- multiple sessions can be active concurrently;
- an Objective can branch into independently resumed lines of work;
- a workspace has multiple users;
- cross-device resume is required;
- a complete interactive context UI is introduced;
- frame storage or reconstruction cost becomes material; or
- concurrent creation needs deterministic branch-head arbitration.

A redesign must preserve append-visible history or equivalent auditability,
typed object references, explicit pins and exclusions, inclusion explanation,
stale-state signaling, protected-context separation, repository-current
validity checks, and the rule that user context governance cannot manufacture
scientific authority.

## Related canonical concepts

- [SessionFrame and active context](session-frame-and-active-context.md)
- [Context reconstruction and continuity](context-reconstruction-and-continuity.md)
- [Retrieval strategy and scaling](retrieval-strategy-and-scaling.md)
- [From research state to active context](from-research-state-to-active-context.md)
- [Product surface and bootstrap boundary](product-surface-and-bootstrap-boundary.md)

## Implementation orientation

The schema is in `src/schemas/research/session_frame.py`; repository behavior is in
`src/repositories/research/session_frame.py`; projection and successor helpers
are in `src/memory/session_frame.py`; Planner selection and successor proposals
are in `src/agents/planner/nodes.py`; and graph checkpoint configuration is in
`src/agents/planner/graph.py`. Focused behavior is exercised in
`tests/memory/`, `tests/agents/planner/`, `tests/application/validity/`, and
`tests/architecture/`.
