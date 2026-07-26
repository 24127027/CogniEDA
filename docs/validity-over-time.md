# Validity over time

Scientific validity is not a permanent property attached to an object at
creation. A result is authoritative only while the data state, analytical view,
observed Evidence, provenance, and lifecycle conditions that support it remain
eligible for the current operation.

> **Implementation status:** authorized propagation from the supported source
> and event matrix, dependent lifecycle effects, historical retention, and
> active exclusion are **Implemented** and **Verified on SQLite**. The
> user-facing review, notification, remediation, and complete project-resume
> experience is **Partially implemented**. A production validity-authority
> issuer and production identity provider are **Unsupported**.

The governing rule is:

> Invalidated or superseded scientific objects remain historical, but they must
> be excluded from active authority.

This rule preserves CogniEDA's priority order:

1. conclusion validity and traceability;
2. context type safety; and
3. multi-session project continuity.

Continuity is never permission to restore stale authority merely because an
object appeared in an earlier session.

## Historical truth-to-record and active authority are different

Suppose a churn analysis was correctly recorded: the approved method ran
against a particular DataProfile and AnalysisFrame, produced Evidence, and led
to an admitted Discovery. Later, the team finds that the AnalysisFrame applied
the wrong cohort filter.

Two facts now coexist:

- the historical record still truthfully describes what was run and what was
  concluded at that time; and
- the result is no longer eligible to influence current work because its
  supporting analytical view lost authority.

Deleting the old objects would destroy the first fact. Leaving them active would
violate the second. Validity propagation therefore changes lifecycle and review
metadata while preserving the admitted scientific payload and provenance.

This is not a claim that the old Discovery is ontologically false in every
possible setting. It says that the Discovery cannot remain active under the
current governed research state.

## What validity propagation does

The current path begins with a typed command bound to durable authority and an
exact source state. It deterministically discovers the affected lineage and
commits the supported effects with an immutable ValidityEvent.

Conceptually:

```text
typed validity command
+ authenticated principal and durable authority
+ exact source-state fingerprint
-> deterministic affected-object plan
-> immutable ValidityEvent
-> atomic dependent-state updates
```

The contract version is `validity-propagation/v1`.

Validity propagation is:

- an authorized lifecycle operation;
- a deterministic lineage and effect calculation;
- immutable provenance for why authority changed;
- an atomic state transition on the supported SQLite boundary; and
- a replayable, conflict-detectable command.

It is not deletion, historical claim rewriting, automatic reinterpretation, a
generic event bus, or a shortcut for authoring replacement scientific claims.

## Supported sources and events

Current source accepts four validity-source types. The event/source allowlist is
closed rather than caller-extensible.

| Source | Supported concern | Source result |
| --- | --- | --- |
| DataProfile | invalidation | lifecycle becomes invalidated |
| DataProfile | supersession by a persisted same-dataset replacement | lifecycle becomes superseded and records the replacement |
| Evidence | invalidation or conflict | lifecycle becomes invalidated |
| Evidence | supersession by persisted same-Hypothesis, same-DataProfile Evidence | lifecycle becomes superseded and records the replacement |
| AnalysisFrame | invalidity or provenance corruption | validity becomes invalidated |
| ExecutionRun | execution conflict or provenance corruption | validity becomes conflict |

A reason may identify an implementation defect, method defect, user-authorized
integrity finding, or stronger replacement, but the reason does not expand the
closed event/source matrix.

Direct Discovery invalidation and Discovery deprecation are not supported
validity-command sources. Discovery deprecation exists as a lifecycle and
retrieval-policy state, but current source exposes no validity command that
authors it. Assumption replacement is also outside the validity source matrix.

## How affected state is determined

The validity repository traverses persisted references rather than accepting a
caller-supplied list of dependents. It starts from the source and follows the
implemented lineage through relevant AnalysisFrames, ExecutionRuns, Evidence,
evaluation controls, active admission claims, Discoveries, Hypotheses, Tasks,
and SessionFrames.

This separation protects two invariants:

- a caller cannot omit an inconvenient dependent from the requested effect set;
  and
- the event can record the complete deterministic plan actually used by the
  transaction.

The traversal also fails closed when an affected evaluation or Discovery
references missing Evidence. Silently continuing would leave the system unable
to prove that the effect set was complete.

The current traversal is relational and partly inspects complete result sets for
JSON-held references. It is suitable for the present SQLite-local graph, not a
claim of scalable graph traversal.

## What happens to dependent state

The effect depends on both the source and the dependent's current lifecycle.

| Dependent | Current effect |
| --- | --- |
| Evidence downstream of another source | active or historically scoped Evidence becomes invalidated |
| EvaluationControl | pending, claimed, proposal-ready, retryable-failed, or committed control becomes invalidated |
| DiscoveryAdmissionClaim | pending or claimed admission becomes invalidated |
| governance decision | retained as historical decision provenance; not consumed or rewritten by propagation |
| Discovery | affected non-deprecated Discovery becomes invalidated and receives review provenance |
| Hypothesis before Discovery | ready-for-evaluation state returns to awaiting additional Evidence |
| Hypothesis after Discovery or in another state | lifecycle is retained and a review reason is added |
| Task | lifecycle is retained and a review reason is added |
| SessionFrame | affected non-archived frame becomes superseded and receives a stale-context marker |

The source, all applicable dependents, and the ValidityEvent commit together.
No replacement Evidence, Discovery, Hypothesis, Task, or SessionFrame is created
by this transaction.

## Evidence losing authority removes Discovery authority

The load-bearing case is:

```text
Evidence loses authority
-> its dependent Discovery cannot remain active
```

Evidence is the observed analytical result on which a Discovery's claim rests.
If that Evidence becomes invalidated or superseded, preserving the Discovery as
active would leave a claim whose recorded support is no longer admissible.

The transaction therefore preserves the Discovery's structured claim, scope,
epistemic status, validity basis, and original Evidence references, while
changing its lifecycle to invalidated and recording why review is required.
Repository-by-ID and lifecycle-aware list operations can still retrieve the
historical objects. Active retrieval excludes them.

A replacement Evidence record does not automatically create a replacement
Discovery. A new durable claim must pass protected evaluation, exact governance,
and atomic admission under eligible lineage. Because one Hypothesis admits at
most one Discovery, a post-Discovery replacement generally requires an
appropriate successor Task/Hypothesis path rather than overwriting the old
claim.

## DataProfile and AnalysisFrame changes preserve scope

A Discovery is valid within the data state and analytical view recorded in its
validity basis. A DataProfile change can affect:

- AnalysisFrames derived from that profile;
- ExecutionRuns using those frames;
- Evidence, Hypotheses, and Tasks bound to the profile;
- Discoveries whose validity basis names the profile or affected frames; and
- SessionFrames carrying those objects or summaries.

When an old DataProfile is superseded, the old Discovery remains historically
scoped to it. The new profile does not silently migrate the old claim into a new
data state. Current work must use a new analytical path appropriate to the new
profile.

An invalid AnalysisFrame similarly removes authority from downstream
observation and claim state without asserting that every proposition about the
underlying dataset is false.

Creating and accepting replacement DataProfiles is only a partial product
workflow. Executable DVC integration and governed cleaning are **Deferred**.
Preprocessing that changes data must still create a new dataset version and a
new DataProfile; overwriting an old profile would destroy the scope boundary.

## Replacing an Assumption is different

An Assumption may guide planning, but protected Discovery synthesis excludes
Assumptions. Therefore:

> Replacing an Assumption does not automatically invalidate a scientifically
> valid Discovery.

Current source supports Assumption lifecycle updates, replacement identity, and
active-only planning selection. It does not include Assumptions in validity
dependency traversal and does not automatically invalidate Discoveries when an
Assumption is replaced.

The replacement may legitimately change future planning. Related Tasks may need
review, an existing SessionFrame may become contextually stale, or the user may
want conflict review. Automatic Task review, frame refresh, and notification
from Assumption replacement are **Design target** behavior, not current validity
effects.

This distinction is deliberate. If an Assumption could invalidate a Discovery
merely because it once influenced planning, planning context would become a
hidden inference premise.

## Why history is retained instead of deleted

Destructive deletion appears simpler because the invalid object can no longer be
retrieved accidentally. It fails because it also removes:

- the exact conclusion that was once admitted;
- its supporting and contradicting lineage;
- the reason later work changed course;
- the ability to audit a prior decision; and
- the evidence needed to distinguish correction from fabrication.

The current decision retains immutable scientific content and changes active
authority through explicit lifecycle metadata and ValidityEvent provenance. The
tradeoff is that every active read must enforce lifecycle policy. Historical
storage alone is not safe; active exclusion is equally load-bearing.

## Current limitations

- **Implemented:** the closed source/event matrix, deterministic dependency
  traversal, dependent propagation, historical retention, and repository-backed
  lifecycle exclusion.
- **Verified on SQLite:** atomic rollback, exact replay, overlapping replay,
  changed-command conflict, event immutability, and covered retrieval effects.
- **Implemented:** Task and Hypothesis review reasons, stale-frame markers, the
  runtime propagation facade, and typed context-reconstruction seams.
- **Partially implemented:** the product workflows that issue validity
  authority, surface review consequences, and reconstruct a replacement active
  context.
- **Known deviation:** a SessionFrame containing an affected Discovery only in
  `user_pins` may remain active-status. Retrieval still excludes the invalid
  Discovery.
- **Unsupported:** a general production validity-authority issuer, production
  identity provider, automatic review queue, notification delivery, automatic
  successor frame for each validity change, and complete workspace resume.
- **Deferred:** persistent semantic-index invalidation, Graph Miner dependency
  traversal, cross-workspace propagation, and distributed validity processing.

## Revisit triggers

Reevaluate the implementation when another database backend is supported,
multiple writer processes become a normal deployment, dependency plans become
large, cross-workspace lineage appears, partial invalidation is required, or
replacement claims need explicit supersession chains.

Immediate frame refresh, durable notification delivery, external caches, and
semantic indexes would also add consumers that must observe the same authority
cutover. Any redesign must preserve authorization, deterministic effect
planning, all-or-nothing propagation, immutable provenance, historical
retention, and active exclusion.

Continue with
[Atomic validity propagation](atomic-validity-propagation.md) for transaction,
fingerprint, replay, and concurrency mechanics, then
[Invalidation and active retrieval](invalidation-and-active-retrieval.md) for
the authority boundary at read time.

## Related decision rationale

The tradeoff between retained history and active exclusion is summarized in
[Design decisions and tradeoffs](design-decisions-and-tradeoffs.md#15-historical-retention-and-active-exclusion).
[ADR-005](decisions/ADR-005-atomic-validity-propagation.md) records the atomic
validity decision and its redesign constraints.

## Implementation orientation

The primary implementation boundaries are `src/application/validity/`,
`src/schemas/validity/`, `src/repositories/validity/`,
`src/db/models/validity.py`, and `src/memory/`.

Focused verification is under `tests/application/validity/`,
`tests/repositories/`, `tests/memory/`, `tests/architecture/`, and
`tests/e2e/`.
