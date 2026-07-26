# Active retrieval after invalidation

Validity propagation and retrieval solve different halves of the same safety
problem:

```text
validity propagation changes active authority
retrieval policy enforces the resulting authority state
```

> **Implementation status:** lifecycle-aware Discovery retrieval,
> mode-specific context policy, invalid-state exclusion, pin safety,
> superseded-frame rejection, and historical repository reads are
> **Implemented**. Covered propagation and exclusion behavior is
> **Verified on SQLite**. Durable review signals are **Partially implemented**;
> automatic frame refresh, notification delivery, and a user review workflow are
> **Unsupported**.

Historical preservation without active exclusion would allow stale conclusions
to keep influencing work. Active exclusion without historical preservation
would erase the reason the project changed course. CogniEDA requires both.

## Transactional state and retrieval policy are separate

The validity transaction commits source and dependent lifecycle changes. It
does not update a semantic index, push an event-bus notification, or rewrite
every cached presentation.

The current retrieval path reads repository state and applies policy before
relevance scoring:

```text
load bounded candidates and explicit structural references
-> apply user exclusions
-> re-read Discovery lifecycle state
-> exclude invalidated or deprecated Discoveries
-> evaluate profile and motivation eligibility
-> score and rank remaining candidates
```

This order makes ranking downstream of authority. A high semantic score, direct
Task relationship, or user pin cannot compensate for invalid lifecycle state.

## What active retrieval excludes

Current policy distinguishes object type, lifecycle, and context mode.

- Invalidated and deprecated Discoveries are excluded from Planning and Answer
  Context.
- Superseded and invalidated Evidence is excluded from normal current context.
- Superseded DataProfiles are not current enough for active context.
- Superseded and archived SessionFrames cannot produce supported projections.
- Existing Discoveries are excluded from protected Conclusion and Discovery
  Synthesis Context regardless of lifecycle because new claims must be
  synthesized from Hypothesis, current DataProfile, provenance, and active
  Evidence.
- Assumptions remain planning-only.

Flagged Discoveries are different from invalidated ones. Planning may surface a
flagged Discovery for review, but current bounded retrieval makes it ineligible
to motivate a Task. Answer Context excludes it pending review.

Discovery deprecation is enforced by retrieval policy, but no supported
validity command currently creates that lifecycle transition. It must not be
described as a completed deprecation workflow.

## Historical state remains available

Invalidation does not delete the source, dependent scientific objects, or the
ValidityEvent. Repository by-ID lookup and lifecycle-aware list operations can
retrieve invalidated or superseded DataProfiles, Evidence, Discoveries, and
SessionFrames for explicit inspection.

That is a library-level historical path, not a complete historical-query
product. There is no dedicated audit context mode, UI, CLI, or API that guides a
user through historical state. The repository access is **Implemented**; the
general historical exploration experience is **Unsupported**.

## Pins influence selection, not authority

A SessionFrame pin says that the user wants a Discovery considered. It gives a
valid Discovery strong structural priority and brings it into the bounded
candidate pool.

A pin does not:

- change Discovery lifecycle;
- reactivate invalid Evidence;
- make an invalidated or deprecated Discovery admissible;
- make a flagged or wrong-profile Discovery eligible to motivate work; or
- enter protected scientific evaluation.

When repository-backed retrieval encounters a pinned invalid Discovery, it
excludes the object before scoring and records an exclusion note identifying
the pin and lifecycle state.

This is the correct asymmetry: user intent is retained as history, while
scientific authority remains governed by current state.

## Affected SessionFrames

Validity dependency discovery scans typed references and summaries held by
SessionFrames. An affected non-archived frame is changed to superseded and
receives a stale-context marker tied to the ValidityEvent.

The historical frame remains readable by ID, but:

- latest-active selection will not return it;
- `SessionContextBuilder` rejects it for supported context modes; and
- a caller must choose or construct another eligible frame.

The validity transaction does not automatically create a successor frame. It
also does not deliver a notification or open a user review queue.

## Mandatory pin-only stale-frame review

The dependency scan checks DataProfile, Evidence, Discovery, Hypothesis, and
Task references and summaries. It does not inspect `user_pins`.

Therefore a frame containing an affected Discovery identifier only in
`user_pins` may retain active-status after the Discovery becomes invalid.

The current behavior is:

1. The historical pin remains in the frame.
2. The frame is not selected as affected solely because of that pin.
3. No stale marker is appended to that frame.
4. No successor frame is created.
5. No notification is delivered.
6. Repository-backed Discovery retrieval resolves the pin, re-reads the
   Discovery's current lifecycle, excludes it, and emits an exclusion note.
7. The invalid Discovery cannot become a motivation or context candidate.

Classification:

```text
B. AUTHORITY SAFE, CONTEXT FRESHNESS PARTIAL
```

The dependency scanner misses a context-freshness signal, not a route that
restores scientific authority. This is a known limitation for a future
SessionFrame-governance or validity-product package. Changing dependency
scanning is outside the current documentation package.

## Stored summaries and repository-current authority

`SessionContextBuilder` projects lifecycle data already stored in a
SessionFrame. It does not query repositories. Safety therefore depends on
affected frames becoming superseded when they carry scientific summaries or
typed references.

`DiscoveryRetrievalEngine` is different: it resolves Discovery identifiers
through the repository and evaluates the current lifecycle before scoring.
That repository-current read is what makes the pin-only case authority-safe.

The distinction should remain explicit:

- a SessionFrame is a snapshot and selection aid;
- the frame is not proof that selected objects remain current; and
- supported active retrieval must revalidate repository authority.

An external cache or future semantic index would need an equally explicit
invalidation or repository revalidation boundary.

## Review signals that exist

Validity propagation currently leaves several durable review signals:

- affected Tasks retain lifecycle and gain a review reason;
- affected Hypotheses gain a review reason and may return to awaiting
  additional Evidence before Discovery;
- affected Discoveries record review provenance and affected Evidence IDs;
- affected SessionFrames receive a stale marker and become superseded; and
- retrieval emits an exclusion note when it encounters an invalid pin.

These records make the reason for exclusion inspectable. They do not constitute
a complete user-facing remediation workflow.

No current source provides:

- automatic notification delivery;
- a durable review inbox;
- a guaranteed successor SessionFrame;
- automatic replacement analysis;
- immediate refresh of every open context;
- semantic-index invalidation; or
- complete project resume after remediation.

Those capabilities are **Unsupported** or **Deferred**, depending on the
surrounding product design.

## Why invalid state is excluded rather than merely down-ranked

Down-ranking looks attractive because it preserves recall and lets relevance
resolve ambiguity. It fails for invalid authority: a sufficiently strong pin,
structural relationship, or semantic score could bring the object back.

The current decision removes invalidated and deprecated Discoveries before
ranking. The tradeoff is that ordinary retrieval cannot use them for comparison
or audit. A future explicit historical or comparative mode may admit them, but
it must label their authority and prevent them from silently motivating current
work.

## Why frames are preserved when stale

Rewriting a SessionFrame in place would make it difficult to reconstruct what
the user had selected before the validity change. Deleting it would erase
context history.

The current decision preserves the snapshot and changes lifecycle metadata when
the dependency scan can prove it is affected. The tradeoff is incomplete
freshness when a relationship exists only in an unscanned field such as
`user_pins`.

Revisit this boundary when immediate context refresh becomes product-critical,
frame ownership expands to multiple users or branches, or review notifications
must be reliable. Any change must preserve the rule that a stale frame cannot
restore invalid authority.

## Continuity after exclusion

The implemented continuity ingredients are:

```text
durable typed objects
+ immutable provenance
+ current lifecycle state
+ active retrieval policy
+ reconstructed SessionFrame projection
```

A later caller with the same database can inspect the ValidityEvent, load
current objects, select the latest eligible frame, and build a bounded
projection. Repository-current retrieval then reflects the Discovery lifecycle
that exists after propagation.

This is durable continuity, not full product resume. Automatic workspace
opening, restored chat, durable Planner checkpoints, user-specific latest-frame
selection, and guided remediation remain incomplete or unsupported.

Continue with
[From validity change to active context](validity-change-to-active-context.md)
for the running churn workflow. The broader SessionFrame and ranking contracts
remain owned by
[SessionFrame and active context](../context/session-frame.md),
[Context type safety and retrieval](../context/context-type-safety.md), and
[Context continuity and resume](../context/continuity-and-resume.md).

## Implementation orientation

Validity effects are owned under `src/application/validity/`. SessionFrame
persistence and projection are under `src/repositories/research/session_frame.py`
and `src/memory/`. Discovery historical reads and lifecycle-aware candidate
loading use the Discovery repository.

Focused verification is under `tests/application/validity/`, `tests/memory/`,
`tests/architecture/`, and `tests/e2e/`.
