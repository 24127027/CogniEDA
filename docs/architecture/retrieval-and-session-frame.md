# Retrieval and SessionFrame

> **Role:** Technical reference. **Canonical concept owner:**
> [Context type safety and retrieval](../concepts/context/context-type-safety.md).
> **Contributor entry:** [Contributor documentation](../development/index.md).
> **Current-state owner:** [CogniEDA current state](../current-state.md).

> **Implementation status:** bounded Discovery retrieval and typed projections
> are **Implemented**; the general session-resume product workflow is
> **Partially implemented**.

Canonical reader explanations:
[SessionFrame and active context](../concepts/context/session-frame.md),
[Context type safety and retrieval](../concepts/context/context-type-safety.md),
[Retrieval strategy](../concepts/context/retrieval-strategy.md),
[Context continuity and resume](../concepts/context/continuity-and-resume.md),
[SessionFrame scaling and resume limits](../concepts/context/session-frame-scaling.md), and
[Active retrieval after invalidation](../concepts/validity/active-retrieval-after-invalidation.md).
This page retains the concise source-oriented reference.

## Current SessionFrame behavior

`SessionFrame` is a persisted context snapshot. `SessionFrameRepository` can append, read, list,
and select the latest active/checkpoint/handoff frame. Planner approval paths can append successor
frames; atomic Discovery admission creates a deterministic conclusion frame; validity propagation
marks affected frames `SUPERSEDED` and appends a stale marker.

Ordinary successor creation does not mark the predecessor superseded; recency selects the latest
snapshot. Frames are not updated in place during ordinary “resume.” There is no supported
workspace-open UI, automatic timestamp refresh, or general item-governance service.

## Context projections

`SessionContextBuilder` builds planning, answer, conclusion, and discovery-synthesis views.
Assumptions are planning-only. Existing Discoveries are allowed for answer/planning under policy
but excluded from conclusion/discovery synthesis. Rejected Tasks, completed Hypotheses, invalid
Evidence, stale caches, and superseded frames are excluded as defined by `retrieval_policy.py`.

The protected Hypothesis Analyst path does not consume SessionFrame projections; it uses the
closed repository-built bundle described in
[Protected evaluation](../concepts/scientific-lifecycle/protected-evaluation.md). Current production
`SessionContextBuilder` call sites request Planning Context only.

## Discovery retrieval

`DiscoveryRetrievalEngine` loads explicit structural references plus a bounded recent relational
window, then applies exclusions and lifecycle policy in memory before structural and lexical
scoring. It is used by Planner root-Task motivation and decomposition.

Invalidated/deprecated Discoveries remain available through explicit repository historical reads
but are excluded from active retrieval even when pinned. A profile mismatch is warned and made
context-only rather than removed before ranking; no independent operation-scope filter exists.
The request's Objective and SessionFrame identifiers do not filter the repository query. A
superseded SessionFrame is not returned by `get_latest_active`, and supported Planner call sites
reject it before retrieval.

Operational ranking, budget distortion, commit-time profile revalidation, and
semantic-scaling triggers belong to the retrieval-strategy owner above. Frame
selection, global latest semantics, checkpointing, and product resume belong to
the SessionFrame-scaling owner.

## Deferred work

**Known deviation:** No independent operation-scope filter exists in the current
request or retrieval path.

**Deferred:** The complete typed operation-scope policy, Graph Miner traversal,
persistent semantic/vector indexes, a general historical query mode, explicit
comparative scope, session scoping/cardinality policy, and a user-facing resume
interface.
