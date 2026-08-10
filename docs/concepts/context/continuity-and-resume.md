# Continuity and resume

Continuity is reconstruction of governed research state across sessions,
pauses, restarts, and worker failures. It is not replay of a conversation and
not a request for an agent to remember what happened.

This page defines the **target design** for multi-session reconstruction,
concurrency, restart, replay, leases, fencing, and pending work. It does not
prescribe a database or message transport.

## Governed reconstruction

Resume recovers, as applicable:

- Objective;
- active PlanRevision;
- Task lifecycle and dependency state;
- ScientificInvestigationRun;
- active protocol revision;
- Evidence obligations;
- pending EvidenceRequests;
- admitted Evidence;
- protected outcome and governance state;
- validity events and review obligations;
- approval holds and exact proposal identity;
- leases and fencing state;
- pending outbox and inbox work;
- current SessionFrame;
- permitted next actions.

The recovered projection may also include normalized outcomes, blockers,
limitations, attempt lineage, and stale GeneratedViews. Every item retains its
typed identity and authority.

## Prose is not authority

A handoff summary, chat transcript, model explanation, or GeneratedView may
help a user understand the recovered state. It cannot establish that a plan
was approved, a protocol was active, Evidence was admitted, governance
authorized a proposal, a lease was owned, or a validity restriction was
cleared.

If the necessary durable record or exact binding is missing, resume fails
closed and exposes a recovery blocker. It does not infer authority from the
most plausible narrative.

## Workspace, Objective, and session concurrency

One Workspace may contain multiple concurrently active Objectives. Sessions
may work concurrently when bound to different Objectives.

For the current architecture phase:

```text
at most one active Planner session per Objective
```

This constraint protects Objective-scoped planning ownership and does not
generalize to one session per Workspace. A Planner session must hold explicit
operational ownership of its Objective; another session may inspect authorized
historical state or work on a different Objective without acquiring that
ownership.

Specialist workers and execution attempts have their own bounded operational
ownership. Their leases do not turn them into Planner sessions or scientific
authorities.

## Restart-safe durable state

State needed to determine the next authorized transition must survive process
loss. Restart reconstructs from durable identities, lifecycle transitions,
outbox and inbox state, approvals, attempts, validity events, and SessionFrame
selection.

No transition may depend solely on hidden in-memory agent state. A restart may
recompute a projection or regenerate a GeneratedView, but it must not recreate
an authoritative scientific record from prose.

## Idempotent replay and duplicates

Replaying the same admitted command, approval, dispatch intent, returned
result, governance decision, or validity event must not create a duplicate
semantic object or repeat a transition.

Duplicate-result handling compares exact work, attempt, source, fencing,
contract, and digest identity. An exact duplicate may be acknowledged without
another transition. A different result for the same claimed identity is a
conflict or integrity failure, not a second candidate chosen by convenience.

Retry and replay remain distinct:

- **replay** re-applies durable history idempotently to reconstruct progress;
- **retry** creates a new traceable execution attempt under explicit authority
  after the prior attempt ended or lost ownership.

## Leases and fencing

A lease grants temporary operational ownership of bounded work. A fencing
token or epoch prevents a stale worker from advancing state after ownership
has moved to a newer claimant.

Leases and fencing protect execution ordering and session ownership. They do
not create scientific authority, approve a plan, admit Evidence, authorize a
Discovery, or restore validity. Those acts still require their own exact
contracts and authorities.

Lease recovery may reclaim expired work, create a governed retry, or produce a
typed ending. It must retain attempt lineage and must not accept a late result
from a stale worker as current merely because the computation succeeded.

## Outbox and inbox recovery

An outbox preserves an admitted dispatch intent so a crash after commit does
not lose executable work. An inbox preserves returned messages or results with
source, attempt, digest, and processing identity so receipt and durable
transition can be replayed safely.

On restart, the system identifies pending, claimed, returned, processed,
failed, stale, or ambiguous work according to the applicable lifecycle. It
does not send every command again or admit every stored result.

## Pause, approval, and resume

Pausing preserves exact active state and permitted next actions. Approval
holds preserve the exact proposal or plan version presented for decision. A
resumed decision applies only to that identity; any substantive change
requires a new proposal and the applicable approval.

SessionFrame successors preserve cumulative historical membership while active
selectors may change. Context reconstruction applies current validity and
eligibility when selecting a bounded run projection; being omitted from one run
does not delete a historical reference or conversation segment.

The bounded runtime's `ConversationSegment` is an indivisible history and
context-selection boundary compatible with future interruption work. It is not
a durable execution checkpoint. Full interrupted-run state, leases, and resume
protocol remain separate recovery machinery.

## Fail-closed recovery

Recovery stops or narrows the next actions when it cannot establish:

- Objective and active Planner-session ownership;
- active plan or proposal identity;
- Task and investigation lineage;
- protocol revision and Evidence obligations;
- attempt, lease, fencing, or result identity;
- governance or approval binding;
- current validity and permitted use.

The system returns a typed recovery blocker or review requirement. It does not
fill gaps by replaying conversation, selecting the newest record, or asking a
model to infer intent.

## Implementation status

**Partially implemented.** The retained in-process `Session` now preserves
cumulative SessionFrame successors and complete ConversationHistory while
selecting whole coherent segments for each request. Deterministic turns need no
fabricated model history. This is not restart-safe continuity or an interruption
engine. Other operational foundations include
append-only SessionFrame snapshots; durable PlannerOperation approval and
resume checks; atomic commit for a bounded operation set; paired
ExecutionRun/outbox admission; leases, fencing epochs, retry lineage, and
idempotency fields. These foundations protect some restart and duplicate-
delivery cases.

Canonical PlanRevision, ScientificInvestigationRun, protocol and
EvidenceRequest recovery, complete inbox replay, Objective-bound SessionFrame
queries, one-active-Planner-session-per-Objective enforcement, governance and
validity-event reconstruction, and full permitted-next-action projection are
incomplete or absent. The target continuity flow is not implemented end to
end.
