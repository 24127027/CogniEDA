# Propagating validity changes atomically

Decision ID: D-005

**Decision classification:** Durable architectural decision.

**Implementation status:** **Verified on SQLite** for the supported validity
event matrix.

## Context

Scientific records can lose active authority after admission. A DataProfile can
be superseded, Evidence can be invalidated, or a Discovery can be superseded.
Historical identity and provenance must remain available while active retrieval
stops using state whose validity basis no longer holds.

## Problem

Validity crosses several record types. Updating only the source can leave a
dependent Discovery retrievable, a SessionFrame apparently fresh, or a pending
admission able to commit against stale authority. Deleting records removes the
evidence needed to explain what was once concluded and why it changed.

## Failure mode

An invalid Evidence row remains an active premise, a stale frame silently
restores an invalid pinned Discovery, an admission race commits after its source
changed, or a retry applies a different dependent-effect set under the same
event identity. Scientific visibility and durable history diverge.

## Tempting alternatives

- delete invalid or superseded rows;
- rewrite scientific payloads in place;
- update each repository independently;
- let retrieval eventually notice validity changes;
- treat SessionFrame status as authority over current repository validity; or
- use event identity alone without source, request, plan, and effect
  fingerprints.

These approaches trade immediate simplicity for untraceable or partially
visible truth.

## Decision

Validity transitions retain historical records and exclude inactive state from
active reasoning. Scientific payloads remain unchanged; lifecycle,
supersession, review, and context-freshness metadata record the transition.

`AtomicValidityPropagationService` is the sole supported transaction owner for
the source transition, deterministic dependent effects, immutable
`ValidityEvent` insertion, and affected admission-claim conflict handling.
It:

1. validates typed command authority and the source fingerprint;
2. constructs and fingerprints the deterministic effect plan;
3. applies source and dependent compare-and-set updates;
4. records request, plan, event, and effect identity;
5. marks affected SessionFrames stale and prevents invalid state from active
   retrieval; and
6. commits the immutable event and all effects together.

Exact replay requires the full persisted effect set to match. A command with
changed meaning conflicts. Validity propagation has no separate claim, lease,
or fencing protocol; when a Discovery admission claim is affected, that claim's
existing fencing epoch is a dependent compare-and-set input rather than
validity-service authority.

SessionFrame governs selection and handoff, not validity. A pin cannot make an
inactive object scientifically current. Invalidation never deletes the
historical object.

## Invariant protected

Historical presence is not active authority. A validity transition changes the
visible scientific state, dependent lifecycle state, context freshness, audit
event, and conflicting in-flight admission state atomically.

## Current implementation

Typed commands, durable authority checks, deterministic plans, and the
transaction owner live under `src/application/validity/`. Supported repository
methods stage lifecycle effects without changing immutable scientific content.
SQLite triggers prevent update or deletion of `ValidityEvent` rows and reinforce
selected lifecycle constraints.

Retrieval validates repository-current state before scoring and excludes
invalid or superseded candidates. Focused tests cover each supported source
type, authority failure, rollback, exact replay, changed replay, races,
scientific-payload preservation, frame staleness, and retrieval exclusion.
Architecture tests constrain dependency direction and supported writers.

## Tradeoffs

Retaining history increases storage and requires active/inactive filtering at
every authoritative read. Atomic propagation coordinates several repositories
and can reject work that an eventually consistent design would accept
temporarily. The benefit is explainable history without a window of false
scientific authority.

## Known limitations

- Atomicity is **Verified on SQLite**; backend portability is **Deferred**.
- Supported services preserve scientific payloads, but no universal database
  trigger blocks every direct update to DataProfile, Evidence, Discovery, or
  SessionFrame content.
- A pin-only SessionFrame can remain active in stored frame state even after its
  pinned Discovery becomes invalid; repository-current retrieval still excludes
  that Discovery. This is a **Known deviation** in frame freshness behavior.
- Validity propagation does not automatically author a successor scientific
  claim.
- Retention, archival, and privacy policy are **Unsupported** as a
  complete product capability.

## Risks

A new retrieval path may forget active-state filtering. A future effect may be
left out of the deterministic plan, allowing replay to accept incomplete state.
Treating lifecycle mutation as permission to edit scientific content would
destroy the historical guarantee.

## Revisit triggers

Revisit the mechanism for another backend, distributed writers,
cross-workspace dependencies, large effect sets, archival requirements, or
privacy obligations. Preserve atomic visibility, immutable event history,
scientific-payload identity, deterministic replay, and fail-closed active
retrieval.

## Consequences for future work

All scientific retrieval must validate current lifecycle state before ranking
or synthesis. New validity effects must join deterministic planning,
fingerprinting, compare-and-set execution, rollback tests, and replay
verification. User interfaces should explain retained-but-inactive state rather
than hiding or deleting it.

## Related canonical concepts

- [Design decisions and tradeoffs](index.md)
- [Validity over time](../concepts/validity/validity-over-time.md)
- [Atomic validity propagation](../concepts/validity/validity-propagation.md)
- [SessionFrame and active context](../concepts/context/session-frame.md)
- [Discovery governance and admission](../concepts/scientific-lifecycle/discovery-governance-and-admission.md)

## Implementation orientation

Start with `src/application/validity/`, validity command and event schemas,
participating repositories, active retrieval under `src/memory/`, and SQLite
constraints under `src/db/`. Focused checks live under
`tests/application/validity/`, `tests/memory/`, `tests/repositories/`, and
`tests/architecture/`.
