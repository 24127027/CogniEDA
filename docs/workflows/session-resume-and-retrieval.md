# Session Resume and Retrieval Workflow

> **Implementation status:** Implemented as library-level append/read/projection
> and bounded SQL retrieval. No production workspace-open or UI resume bootstrap
> exists.

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
SQLite structural filtering followed by deterministic lexical scoring. Filters
cover lifecycle/validity state, profile scope, pinning, exclusions, and
motivation eligibility.

- Invalidated or deprecated Discoveries are excluded even when pinned.
- Flagged or cross-profile Discoveries are not eligible to motivate new work.
- Retrieval does not mutate research state.
- Graph Miner and a persistent semantic/vector index are deferred.

## Resume boundary

A caller can reconstruct an active projection by loading the latest active frame
for a session and invoking the context builder. The repository does not yet ship
a CLI, API, or process bootstrap that maps a filesystem workspace open into this
sequence automatically.
