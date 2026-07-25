# Retrieval and SessionFrame

> **Implementation status:** bounded Discovery retrieval and typed projections `[Implemented]`;
> general session-resume product workflow `[Partially Implemented]`.

## Current SessionFrame behavior

`SessionFrame` is a persisted context snapshot. `SessionFrameRepository` can append, read, list,
and select the latest active/checkpoint/handoff frame. Planner approval paths can append successor
frames; atomic Discovery admission creates a deterministic conclusion frame; validity propagation
marks affected frames `SUPERSEDED` and appends a stale marker.

Frames are not updated in place during ordinary “resume.” There is no supported workspace-open UI,
automatic timestamp refresh, or general item-governance service.

## Context projections

`SessionContextBuilder` builds planning, answer, conclusion, and discovery-synthesis views.
Assumptions are planning-only. Existing Discoveries are allowed for answer/planning under policy
but excluded from conclusion/discovery synthesis. Rejected Tasks, completed Hypotheses, invalid
Evidence, stale caches, and superseded frames are excluded as defined by `retrieval_policy.py`.

The protected Hypothesis Analyst path does not consume SessionFrame projections; it uses the
closed repository-built bundle described in [Context Type Safety](context-type-safety.md).

## Discovery retrieval

`DiscoveryRetrievalEngine` performs a bounded relational candidate query with structural and
lexical scoring. It filters lifecycle state, DataProfile scope, pins, exclusions, and Task
motivation eligibility. It is currently used by Planner decomposition.

Invalidated/deprecated Discoveries remain available through explicit repository historical reads
but are excluded from active retrieval. A superseded SessionFrame is not returned by
`get_latest_active`.

## Deferred work

`[Deferred]` Graph Miner traversal, persistent semantic/vector indexes, a general historical query
mode, session scoping/cardinality policy, and a user-facing resume interface.
