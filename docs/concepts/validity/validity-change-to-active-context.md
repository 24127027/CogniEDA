# From validity change to active context

This workflow follows the running churn investigation after a scientific result
has already been admitted.

The original Task asked:

> Test whether longer first-response time is associated with 90-day churn in
> the accepted 2025 small-business subscription cohort, using the approved
> method, parameters, and decision rule.

The analysis produced Evidence and an evidence-bound Discovery. Later, the team
finds an implementation defect in the Evidence-producing path.

> **Implementation status:** the authorized command, deterministic effect plan,
> atomic lifecycle transition, immutable event, active exclusion, and
> repository-current retry behavior are **Implemented** and
> **Verified on SQLite**. Durable review signals and reconstruction seams are
> **Partially implemented**; automatic remediation, successor context, user
> notification, and complete workspace resume are **Unsupported**.

The path is:

```text
authorized validity concern
-> exact source-state validation
-> deterministic affected-object plan
-> atomic ValidityEvent and lifecycle effects
-> active retrieval exclusion
-> stale or unchanged SessionFrame behavior
-> later context reconstruction
```

## 1. An implementation defect becomes a validity concern

Suppose review finds that the calculation behind the Evidence used the wrong
churn-window boundary. The admitted record still accurately says what the
system observed and concluded at the time, but that Evidence must no longer
support current reasoning.

The tempting shortcut is to edit the Evidence result or delete the Discovery.
Editing would rewrite observation history. Deletion would erase the conclusion,
its lineage, and the reason the project changed course.

The current decision is an explicit Evidence invalidation command with a reason
describing the defect. The invariant protected is historical traceability
without continued active authority.

## 2. Exact authority is required

The command names the Evidence, requested event, reason, expected source state,
source fingerprint, workspace/session scope, durable authority, and
idempotency key.

For user-governed invalidation, the service requires:

- the exact authenticated principal supplied by the runtime boundary;
- the same actor identity recorded in the durable authority;
- matching workspace and session;
- an active, unexpired grant for the original execution; and
- purpose and operation scope for that exact Evidence and event.

A trusted internal concern must come from a narrow allow-listed producer and
the same exact source/event scope.

The contract prevents a caller from turning a generic permission into arbitrary
scientific mutation. The in-process runtime facade and verification are
**Implemented**. A general production validity-authority issuer and production
identity provider are **Unsupported**.

## 3. The source state is validated

The service reloads the Evidence and computes its source fingerprint from the
scientific core rather than accepting a caller-declared hash as authority. It
compares both lifecycle and fingerprint with the command.

If the Evidence changed, is no longer active, or no longer matches the expected
fingerprint, a new mutation cannot proceed as the old command. It fails stale.

This guard prevents a plan reviewed for one source state from being applied to
another. Supersession adds the same kind of guard for the persisted replacement.

## 4. The affected-object plan is discovered

The service traverses repository lineage from the Evidence. In this scenario,
the plan can include:

- the Evidence source transition;
- its evaluation control;
- a pending or claimed Discovery admission, if one still exists;
- the dependent Discovery;
- the Hypothesis and Task review records; and
- SessionFrames that carry the Evidence, Discovery, Hypothesis, Task, or
  corresponding summaries and references.

The plan is deterministic and frozen. Its fingerprint commits to the source
binding and ordered transition manifest.

No caller may remove the Discovery from the plan merely to keep a convenient
answer active. No replacement claim is authored by planning the invalidation.

## 5. One transaction changes authority

On the supported SQLite path, the application transaction:

1. invalidates the Evidence;
2. invalidates the affected evaluation and active admission claim;
3. invalidates the dependent Discovery without rewriting its admitted claim;
4. adds review provenance to the Hypothesis and Task;
5. supersedes affected non-archived SessionFrames and adds stale markers; and
6. inserts the immutable ValidityEvent.

The governance decision that once approved the proposal remains historical. It
is not rewritten to pretend that approval never occurred.

All applicable effects commit once or roll back together. A failure cannot leave
an event claiming success while the Discovery remains active, or invalidate the
Discovery while a frame included in the committed propagation plan remains
current.

The event is provenance for the authority change. It is not an FCO, Evidence,
Discovery, or replacement scientific result.

## 6. The Discovery remains historical but loses active authority

After commit, the old Discovery still preserves:

- its exact claim wording;
- cohort and analytical scope;
- epistemic status;
- validity basis;
- Evidence references;
- limitations and uncertainty; and
- creation and governance history.

Its lifecycle is now invalidated, so it cannot be used as active motivation or
answer context. The ValidityEvent and review metadata explain why.

This is the practical meaning of:

```text
historically true-to-record
!= currently authoritative
```

## 7. A pin cannot restore the churn Discovery

Suppose the user had pinned the Discovery in a SessionFrame because it was
important to the churn investigation.

Repository-backed retrieval resolves that identifier, reloads the Discovery,
sees the invalidated lifecycle, excludes it before scoring, and records an
exclusion note. The pin remains evidence of user intent, not scientific
authority.

If the frame also carries the Discovery or affected lineage in the dependency
fields scanned by validity propagation, it becomes superseded and gains a stale
marker. Latest-active selection and context projection then reject it.

If the identifier appears only in `user_pins`, the current dependency scan does
not select the frame. The frame may remain active-status, but retrieval still
re-reads and excludes the invalid Discovery.

Classification:

```text
B. AUTHORITY SAFE, CONTEXT FRESHNESS PARTIAL
```

No automatic successor frame, notification, or review UI is created.

## 8. Later reconstruction uses current authority

A later process can reopen the same SQLite database through the in-process
runtime composition, inspect durable research state, choose the latest eligible
SessionFrame, and invoke the typed context and retrieval helpers.

The reconstructed operation should combine:

```text
active Objective and workflow state
+ current DataProfile
+ Discoveries that still have active authority
+ eligible Evidence and provenance
+ review and stale-context signals
```

It must not replay every old message or trust a SessionFrame identifier as proof
that its pinned objects remain current.

The current library provides durable repositories, latest-active frame
selection, context projection, and repository-current Discovery retrieval. It
does not automatically open a workspace, restore chat, select by user or
Objective, or guide the user through remediation. Durable continuity is
**Implemented**; complete product resume is **Unsupported**.

## 9. A replacement Evidence does not replace the claim

Suppose the defect is corrected and a new Evidence record is admitted. The old
Evidence may be superseded by that persisted same-lineage replacement.

The validity transaction still does not create a new Discovery. Scientific
wording must come from protected evaluation, be authorized by governance, and
be admitted atomically under eligible lineage. Existing one-Discovery-per-
Hypothesis cardinality means post-Discovery correction generally needs an
appropriate successor Task/Hypothesis path.

The simpler alternative—copy the old claim onto the replacement Evidence—would
skip evaluation and assume the corrected result has the same meaning. The
current separation protects scientific authorship and exact support lineage at
the cost of an additional governed analytical cycle.

## 10. Replacing an Assumption follows another path

Now consider a different change: the team replaces the planning Assumption that
“each account has one stable support tier.”

Current source can record the replacement and future planning can exclude the
old Assumption from active planning selection. Protected evaluation never used
that Assumption as a premise, so its replacement does not automatically
invalidate the churn Discovery.

The replacement may justify:

- reviewing Tasks whose plan was shaped by the old belief;
- warning that a SessionFrame contains stale planning context;
- asking the user whether a new analysis is required; or
- changing future decomposition.

Those review and refresh consequences are not implemented as an automatic
validity cascade. Treating them as if they invalidated the Discovery would
violate the boundary between planning input and scientific support.

## 11. What the user can know later

From durable state, a later reader can determine:

- which Evidence lost authority;
- which Discovery was excluded because of it;
- which event and authority changed the lifecycle;
- which Task and Hypothesis require review;
- which directly affected frames are stale;
- which current Discoveries remain available to retrieval; and
- which historical claim and support chain were once admitted.

The reader cannot yet rely on:

- automatic notification that the change occurred;
- a complete remediation queue;
- automatic rerun or successor Hypothesis creation;
- automatic successor SessionFrame creation;
- a semantic index already purged of stale entries; or
- end-to-end workspace resume.

These limits separate scientific authority safety from product-level context
freshness.

## 12. Why this remains SQLite-bounded

The current transaction, CAS, writer serialization, unique-event identity,
rollback, replay, and trigger behavior are verified for SQLite.

Another backend may have different isolation, JSON comparison, lock timing,
uniqueness failure, or retry semantics. Multiple worker processes or very large
dependency graphs may require explicit claims, leases, fencing, chunked plans,
or another coordination design.

No future design may weaken:

- exact authority and source binding;
- deterministic affected-object planning;
- all-or-nothing visible authority;
- immutable validity provenance;
- exact replay and changed-command conflict;
- historical preservation; or
- retrieval exclusion before relevance.

## Implementation orientation

The validity transaction is under `src/application/validity/`, with contracts
under `src/schemas/validity/` and dependency traversal under
`src/repositories/validity/`. Active read enforcement and SessionFrame
projection are under `src/memory/`.

Focused verification is under `tests/application/validity/`, `tests/memory/`,
`tests/architecture/`, and `tests/e2e/`.
