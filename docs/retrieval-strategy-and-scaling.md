# Retrieval strategy and scaling

Retrieval in CogniEDA is a bounded planning aid. It may rank among candidates
that are allowed to appear, but ranking must never decide scientific
admissibility.

> **Implementation status:** Lifecycle-aware bounded Discovery retrieval,
> structural scoring, deterministic lexical fallback, one visible result
> budget, and profile-bound commit revalidation are **Implemented**.
> Operation-specific scope and independent request/frame binding are
> **Partially implemented**. Semantic or vector retrieval, a persistent
> semantic index, and Graph Miner are **Deferred** or **Unsupported**.

[Retrieval and context type safety](retrieval-and-context-type-safety.md) owns
which object types and lifecycle states may enter each context mode. This page
owns the current operational candidate, ranking, budget, and scaling decisions.

## Authority precedes ranking

The durable rule is:

> Retrieval ranking may choose among admissible candidates. It may not make an
> inadmissible Discovery scientifically authoritative.

Lifecycle policy, explicit exclusions, profile compatibility, protected
evaluation construction, and commit-time revalidation remain outside the
scorer. A high lexical score, structural relationship, or user pin cannot
restore an invalidated or deprecated Discovery. A flagged or wrong-profile
Discovery may remain visible as context, but it cannot motivate durable work on
the current path.

## Current retrieval pipeline

`DiscoveryRetrievalEngine` applies this order:

1. Resolve the direct parent Task, its ancestors, and their motivating
   Discovery references.
2. Parse SessionFrame pins and exclusions. Non-UUID notes remain explanatory
   notes rather than becoming object identities.
3. Build a bounded candidate pool from individually fetched structural
   references plus the most recent Discovery window. The defaults are 64 pool
   candidates and eight returned results.
4. Apply explicit exclusions. Exclusion wins over a pin.
5. Apply lifecycle policy. Invalidated and deprecated Discoveries are excluded,
   including when pinned. Flagged Discoveries can remain visible but are not
   motivation-eligible.
6. Add deterministic structural scores: pin `+100`, direct motivation `+10`,
   ancestor motivation `+5`, active-profile match `+2`, and profile mismatch
   `-1` plus motivation ineligibility.
7. Add the scorer result for the request text against the Discovery claim and
   scope.
8. Remove unpinned candidates with a nonpositive total.
9. Sort by total score descending, creation time descending, then UUID
   ascending.
10. Apply one strict `max_results` budget.
11. Return eligible motivation candidates separately from context-only
    Discoveries.

Planner proposal code exposes only motivation-eligible identities for durable
Task motivation. Context-only items remain visible for explanation but cannot
be selected as motivating Discoveries.

## Lexical scoring is a current-stage choice

The default `LexicalScorer` compares normalized token sets. It is
deterministic, inexpensive, locally testable, and easy to explain. The scorer
protocol permits another implementation, but no production semantic scorer,
embedding model, vector store, persistent semantic index, or hybrid retrieval
pipeline is wired today.

Calling the stored score field `semantic_score` or an inclusion reason
“semantically relevant” does not change the implementation. Current retrieval
is lexical ranking after structural and lifecycle handling.

The tradeoff is concrete:

- reproducibility and low operational complexity;
- lower recall for paraphrases, terminology shifts, and multi-hop questions;
- a bounded recent window that can omit an older relevant Discovery; and
- fixed-budget distortion when high-priority or context-only candidates occupy
  slots.

Lexical ranking is a **Current-stage implementation choice**, not an epistemic
invariant. A future scorer may improve recall only after preserving the same
admissibility and explanation boundaries.

## Commit-time revalidation

Root-Task and decomposition commits re-read each selected motivating Discovery.
The commit requires:

- the Discovery still exists;
- lifecycle state is `ACTIVE`;
- scope is nonempty; and
- the validity basis names the exact active bounded `DataProfile`.

The checks occur in the same transaction as the Task operation. A candidate
that became stale after retrieval therefore fails closed rather than
motivating new durable work.

Commit revalidation does not currently prove Objective compatibility,
operation-specific scope compatibility, or an independent binding to the
request's SessionFrame. Retrieval is therefore a proposal aid with a narrow
commit guard, not a complete scientific-admissibility engine.

## Known retrieval deviations

| Item | Classification | Current effect |
| --- | --- | --- |
| deterministic lexical scorer | Current-stage implementation choice | predictable ranking with limited semantic recall |
| bounded recent candidate window | Current-stage implementation choice | bounded cost can miss older unreferenced Discoveries |
| one shared result budget | Current-stage implementation choice | simple visible limit can trade eligible recall for context |
| wrong-profile context-only candidates | Known temporary deviation | cannot motivate work, but can consume result budget |
| request `objective_id` not used as a filter | Known temporary deviation | retrieval does not independently prove Objective compatibility |
| request `session_frame_id` not independently bound | Known temporary deviation | current Planner passes the exact loaded frame, but the engine does not verify that identity |
| no operation-specific scope filter | Deferred design decision | scope text affects ranking; it does not prove operation compatibility |
| semantic/vector index | Deferred design decision | no supported implementation |
| Graph Miner | Unsupported product surface | configuration vocabulary exists, but no executable capability is registered |

These limitations do not currently let an inactive or wrong-profile Discovery
motivate a committed Task after revalidation. If any supported path did allow
that, the defect would block rather than become accepted retrieval debt.

## Scope is not a lexical fact

Claim and scope text both contribute tokens to the lexical score. That makes
scope language discoverable; it does not establish that the proposed operation
is valid within that scope. A complete operation-scope policy needs typed
requirements, an explicit comparison rule, explanation, and commit-time
enforcement.

Until that policy exists, the current safe minimum is exact active-profile and
lifecycle revalidation. Documentation must not describe that minimum as full
Objective, SessionFrame, or operation-scope admissibility.

## Graph Miner and semantic retrieval

The Graph Miner package contains constructor and graph-builder stubs that raise
`NotImplementedError`; its node module has no executable workflow. Configuration
mentions graph-mining skills and tool servers, but configuration is not runtime
capability. The production runtime registers a concrete Data Explorer factory
only and does not register Graph Miner.

Graph traversal, vector similarity, learned reranking, persistent indexes, and
cross-workspace knowledge are therefore **Deferred**. Adding any of them
requires a decision about candidate authority, index freshness after validity
changes, explanation, deterministic fallback, privacy boundaries, replay, and
commit-time revalidation.

## Scaling and revisit triggers

Revisit retrieval when:

- Discovery volume makes the bounded recent window materially lossy;
- measured lexical miss rate becomes material;
- multi-hop explanation is required;
- cross-workspace knowledge is introduced;
- context-only items consume too much of the result budget;
- latency requires a persistent candidate index; or
- an operation-specific scope policy can be expressed and tested.

A redesign must preserve lifecycle-first exclusion, explicit user exclusions,
pin limits, profile and scientific authority, separate context-only results,
visible inclusion reasons, deterministic tie behavior or auditable
equivalence, and commit-time revalidation against repository-current state.

## Related canonical concepts

- [Retrieval and context type safety](retrieval-and-context-type-safety.md)
- [Invalidation and active retrieval](invalidation-and-active-retrieval.md)
- [SessionFrame scaling and resume boundary](session-frame-scaling-and-resume-boundary.md)
- [Planner boundary and operation model](planner-boundary-and-operation-model.md)

## Implementation orientation

The engine is in `src/memory/retrieval_engine.py`; lifecycle policy is in
`src/memory/retrieval_policy.py`; scorer implementations are in
`src/memory/semantic_scorer.py`; and request/result schemas are in
`src/schemas/retrieval.py`. Planner integration and commit revalidation are in
`src/agents/planner/nodes.py` and
`src/application/orchestrator/planner_commit.py`. Focused behavior is exercised
in `tests/memory/`, `tests/agents/planner/`, and `tests/architecture/`.
