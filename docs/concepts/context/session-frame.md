# SessionFrame

`SessionFrame` is the First-Class Object that records structured membership in
a research session. It gives continuity a typed foundation: which research
objects the session has accumulated, which Objective and DataProfile are
active, and which authoritative records a later interaction can resolve.

SessionFrame is not conversation memory and is not a scientific conclusion.
It is user-governed Planner context membership: every retained object must be
resolved and made available to Planner. Each later operation still decides how
that visible object may be used.

This page defines the **Design target**. Exact fields and physical storage are
not part of the conceptual contract.

## What a frame remembers

A SessionFrame may conceptually track references to:

- Objectives and the active Objective;
- planning Assumptions;
- Tasks;
- DataProfiles and the active DataProfile;
- admitted Evidence; and
- Hypotheses and Discoveries when the supported workflow requires them.

The frame preserves membership over time. Moving from one question to another
does not authorize context construction to rank, filter, or truncate retained
members. An object needed as a lineage dependency does not automatically become
a session member merely because another retained object refers to it; authorized
supplemental context may resolve such dependencies without changing membership.

## Membership, selection, and authority

Three questions must remain separate:

```text
Was this object retained and therefore visible to Planner?
  != May this object be used for the current operation?
  != May this object support the current scientific conclusion?
```

SessionFrame membership answers the first question and requires Planner
visibility. Planner context is the resolution of all retained members plus any
authorized supplemental context. Supplemental construction may add but never
silently subtract the frame-derived base.

A purpose-specific use boundary answers the second after applying scope,
lifecycle, validity, lineage, and authority rules. An Assumption remains visible
to Planner but planning-only; a protected `EvaluationBundle` must exclude it.
An answer may refer to an eligible Discovery, while a new protected scientific
evaluation cannot use that Discovery as substitute Evidence.

Scientific authority answers the third question. Selection cannot promote an
Assumption to Evidence, turn raw execution output into admitted Evidence, or
make an invalid Discovery current again. A frame is therefore a continuity
record, not a permission slip.

## Why typed membership matters

Ordinary conversation preserves prose in chronological order. It does not
reliably identify which statement is an Objective, which is an Assumption,
which Task was approved, which data state is active, or which observed result
was admitted as Evidence.

Typed membership lets a later session resolve those questions from
authoritative objects. Conversation can still help interpret what the Human
means, but the system does not have to infer scientific authority from a
transcript.

This also protects history. A referenced Evidence item can remain in the frame
after a later validity event while becoming ineligible for current scientific
use. The frame records that it belonged to the session; validity rules decide
whether it may be used now.

## FCO outside the semantic graph

SessionFrame is one of the eight FCOs, but it is not a semantic Knowledge Graph
node. The graph contains exactly:

```text
Objective
Hypothesis
Evidence
Discovery
```

SessionFrame describes how a research session is organized around scientific
state. It is not itself a scientific proposition, observation, or claim. Its
FCO identity permits durable reference, continuity, succession, and recovery
without misclassifying session organization as knowledge.

## Objective and Workspace boundaries

One Workspace may contain multiple Objectives. Sessions may proceed
concurrently when bound to different Objectives; the current architecture
phase permits at most one active Planner session for a given Objective.

A SessionFrame must not turn Workspace membership into cross-Objective
authority. Material from another Objective can motivate a planning suggestion,
but it cannot silently enter the active Objective as Evidence or Discovery.
Cross-Objective Evidence reuse requires explicit admission under the exact
canonical equality rules.

## Active Objective and DataProfile

The active Objective tells the session which research scope currently governs
coordination. The active DataProfile tells it which admitted data state is
currently selected for applicable work. Both must refer to known frame
membership; neither may be guessed from recency or filesystem location.

Switching the active DataProfile is authority-sensitive because Evidence and
scientific contracts remain bound to the data state they used. A switch does
not rewrite earlier Evidence or make it compatible with the new profile.

## Conversation is separate

Conversation history supports interaction continuity. It may help Planner
understand a follow-up or preserve the native context of a model exchange. It
does not become SessionFrame membership automatically, and SessionFrame does
not store raw chat as research authority.

After restart, authoritative continuity must come from durable typed research
state and its lifecycle. Replaying conversation may aid presentation, but it
cannot reconstruct approvals, admissions, or scientific support that were not
recorded authoritatively.

## Lifecycle and recovery

A session frame may gain membership, change active selectors, be succeeded,
and later be restored. Those changes must remain auditable and must not erase
the earlier truth-to-record.

Recovery resolves every retained reference for Planner visibility, then
reapplies current lifecycle and validity rules to permitted use. Missing
identity, ambiguous successor state, dangling active selectors, or unresolved authority fails
closed rather than being repaired from prose or “latest record” heuristics.

## Current implementation

**Partially implemented.** Current source has a bounded immutable M1-A
`SessionFrame` value containing one optional materialized Objective, ordered
materialized Assumptions, Tasks, Evidence, and Discovery, and one optional
materialized DataProfile. Validated replacement seams protect duplicate
identity and direct Task/DataProfile/Evidence consistency, preserve Discovery
through every successor, and reject duplicate Discovery IDs. Discovery
membership does not require co-retaining its full provenance graph. SQLite can
round-trip bounded frame snapshots including Discovery exactly.

The in-process application exact-copies all six current materialized member
categories into an immutable `PlannerContext`. Planner receives that context,
may return an Objective proposal or exact-text Assumption assessment, and never
receives, mutates, or returns SessionFrame. Application alone applies allowed
results through the existing copy-returning frame seams. Conversation history
remains a separate non-authoritative input to request understanding and is
excluded from protected answer support.

The current value is not the canonical typed-reference membership FCO. It has
no frame identity, Objective-bound session identity, reference manifest,
active Objective/DataProfile selectors distinct from materialized objects,
successor lineage, or runtime reload authority. The in-process application
retains it only for the current process. Canonical durable session continuity
and restart reconstruction remain **Deferred**.

Continue with [Context type safety](context-type-safety.md) for the rules that
govern operation-specific selection and [Continuity and resume](continuity-and-resume.md)
for restart and session ownership.
