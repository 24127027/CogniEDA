# Session Resume and Retrieval Workflow

> **Role:** Technical reference. **Canonical concept owner:**
> [Context continuity and resume](../concepts/context/continuity-and-resume.md).
> **Contributor entry:** [Contributor documentation](../development/index.md).
> **Current-state owner:** [CogniEDA current state](../current-state.md).

> **Implementation status:** **Partially implemented**. Library-level
> append/read/projection, bounded SQL retrieval, and narrow durable approval
> resume exist; no production workspace-open, durable graph checkpoint, or UI
> resume bootstrap exists.

The canonical owner is
[Context continuity and resume](../concepts/context/continuity-and-resume.md);
[Context type safety and retrieval](../concepts/context/context-type-safety.md)
owns admissibility;
[Retrieval strategy](../concepts/context/retrieval-strategy.md)
owns ranking and budget decisions;
[SessionFrame scaling and resume limits](../concepts/context/session-frame-scaling.md)
owns selection and checkpoint limits; and
[Active retrieval after invalidation](../concepts/validity/active-retrieval-after-invalidation.md)
owns validity-change consequences. This page retains the compact technical
sequence.

## SessionFrame snapshots

`SessionFrameRepository` provides append, read, list, latest, and latest-active
operations. A frame is an immutable-style context snapshot: ordinary progress
appends a successor rather than updating a timestamp or focal handles in place.
Atomic Discovery admission appends the conclusion frame. Validity propagation
can mark affected frames `SUPERSEDED` with a stale marker.

`SessionContextBuilder` in `src/memory/session_frame.py` builds bounded planner
projections from a selected frame. These projections may include Assumptions for
planning. They are not the protected conclusion context used by the Hypothesis
Analyst.

## Discovery retrieval

`DiscoveryRetrievalEngine` in `src/memory/retrieval_engine.py` performs bounded
repository-backed candidate loading followed by in-memory lifecycle policy,
structural scoring, and deterministic lexical scoring.

- Invalidated or deprecated Discoveries are excluded even when pinned.
- Flagged or cross-profile Discoveries are not eligible to motivate new work.
- Cross-profile Discoveries may remain warned context-only candidates.
- No independent operation-scope or Objective query filter exists.
- Retrieval does not mutate research state.
- Graph Miner and a persistent semantic/vector index are deferred.

## Resume boundary

A caller can reconstruct an active projection by loading the latest active
frame in the workspace database and invoking the context builder. Current lookup
does not filter by application session, Objective, or branch. The repository
does not yet ship a CLI, API, or process bootstrap that maps a filesystem
workspace open into this sequence automatically.

Durable PlannerOperation and ExecutionApproval records can restore their exact
pending workflow state by identity. The default LangGraph `MemorySaver` cannot
restore arbitrary graph progress after a process restart.
