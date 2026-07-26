# Context type safety and retrieval

Retrieval in CogniEDA is not “find similar text and inject it into a prompt.”
It is the governed selection of typed research state that is currently allowed
to influence one operation.

> **Implementation status:** bounded repository-backed Discovery retrieval,
> lifecycle exclusion, pins and exclusions, deterministic lexical scoring,
> motivation eligibility, and mode-specific SessionFrame projection are
> **Implemented**. Their focused persistence behavior is **Verified on
> SQLite**. Answer retrieval is **Partially implemented**, and independent
> operation-scope filtering is a **Design target**. Graph retrieval and
> persistent semantic indexing are **Deferred**.

The governing order is:

```text
authority and admissibility
  -> epistemic type
  -> DataProfile and operation scope
  -> relevance
  -> bounded context
```

A relevant object that fails an earlier gate must not gain authority from a
later score.

## Three context paths that must remain distinct

Current source contains three related but non-interchangeable mechanisms:

1. `SessionContextBuilder` projects summaries already stored in a selected
   SessionFrame according to a context mode.
2. `DiscoveryRetrievalEngine` queries current Discovery records for bounded
   Planner motivation and context.
3. Protected evaluation reconstructs a closed scientific bundle directly from
   authoritative repositories.

The first two support ordinary reasoning and planning. The third alone supports
Hypothesis Analyst proposal authorship. A generic conclusion-named
`ContextBundle` is not Protected Conclusion Context.

This separation prevents a convenient presentation summary or retrieval result
from becoming an unreviewed scientific premise.

## The current Discovery retrieval pipeline

The implemented engine is planning-specific even though broader policy helpers
define other modes. Its actual sequence is:

```text
planning request
  -> resolve parent and ancestor Task motivation references
  -> parse SessionFrame Discovery pins and exclusions
  -> load explicit structural references
  -> add a bounded recent Discovery window
  -> apply explicit exclusions
  -> apply Discovery lifecycle policy
  -> mark DataProfile match or mismatch
  -> mark flagged state and motivation eligibility
  -> add structural and lexical relevance scores
  -> drop non-positive unpinned candidates
  -> sort deterministically
  -> apply one result budget
  -> separate motivation candidates from context-only results
```

The repository query supplies recent records ordered by creation time and can
fetch explicit Discovery identifiers individually. It does not perform
lifecycle, Objective, DataProfile, or operation-scope filtering in SQL. Those
checks occur in memory/application code after the candidate records are loaded.

Structural references include direct parent-Task motivation, ancestor-Task
motivation, valid Discovery pins, and Discovery references already present in
the frame. Explicit structural references are considered even when they fall
outside the recent candidate window.

## What is rejected before scoring

The engine removes:

- explicit SessionFrame exclusions;
- invalidated Discoveries;
- deprecated Discoveries; and
- references that do not resolve to a Discovery record.

Invalidated and deprecated state wins over a pin. This is a load-bearing
authority rule, not a ranking preference.

The generic retrieval policy also rejects wrong epistemic categories by context
mode. It keeps Assumptions planning-only, excludes rejected Tasks, excludes
evaluated Hypotheses by default, prevents invalid or superseded Evidence from
answer and synthesis contexts, and rejects GeneratedViews and cache records as
reasoning authority.

`SessionContextBuilder` applies both summary memory status and current
lifecycle state when projecting Discovery summaries. It rejects a superseded
or archived frame before constructing any mode-specific projection.

## Profile and scope behavior

When the request supplies an active DataProfile:

- an exact Discovery profile match receives structural credit;
- a different profile is flagged as historically scoped and cannot motivate a
  Task;
- missing profile lineage also prevents motivation; and
- Planner commit re-reads selected motivating Discoveries and rejects a
  lifecycle or DataProfile mismatch that appeared after retrieval.

The different-profile Discovery may still be ranked and returned in the
context-only result set with a warning. This makes the boundary visible and
prevents durable Task motivation, but it is not the stronger target of removing
all wrong-profile state before ranking.

There is also no independent operation-scope field in the current retrieval
request and no compatibility predicate between the requested analytical scope
and `Discovery.scope`. Scope text contributes to lexical scoring, and selected
motivation must have non-empty scope at commit, but that is not semantic scope
isolation.

These are **Known deviation** cases from the stronger validity-first retrieval
design. Cross-profile comparison and explicit scope transfer remain
**Design target** work rather than implicit behavior.

The request also carries Objective and SessionFrame identifiers, but the
current engine does not use either as a repository filter. Workspace isolation
comes from using a separate configured database, not an Objective predicate in
the retrieval query.

## How relevance and ordering work

Current ranking combines transparent structural weights with a deterministic
lexical score:

- a user pin receives the strongest structural priority;
- direct parent-Task motivation outranks ancestor motivation;
- a matching DataProfile adds a smaller structural signal;
- a profile mismatch subtracts a signal and removes motivation eligibility;
- flagged Discoveries remain context-only; and
- token overlap between the query and the Discovery claim plus scope provides
  the lexical component.

The lexical scorer lowercases word tokens and computes set overlap. It uses no
network, embedding model, vector database, or persistent index.

Candidates sort by total score descending, creation time descending, then
Discovery identifier ascending. The final context budget is applied after that
sort. This makes repeated ranking reproducible for unchanged input, including
ties.

Pins influence candidate admission and ranking, not scientific validity.
Exclusions are applied before scoring. A pinned wrong-profile or flagged
Discovery can consume context budget as a context-only item, but cannot be
selected as a Task motivation.

## Context modes and admissible roles

| Mode | May include | Excludes or limits | Current use |
| --- | --- | --- | --- |
| Planning Context | current DataProfiles; proposed, active, or paused Tasks; active planning Assumptions; in-progress Hypotheses; active or flagged Discoveries; active or historically scoped Evidence; workflow warnings | rejected/completed workflow state, invalid/deprecated Discoveries, caches | **Implemented** Planner call sites |
| Answer Context | current DataProfiles, in-progress Hypotheses, active Discoveries, active Evidence, warnings | Assumptions, Tasks, flagged/invalid/deprecated Discoveries, historical Evidence | projection helper **Implemented**; answer workflow **Partially implemented** |
| generic Conclusion Context | accepted current DataProfile, an eligible Hypothesis summary, active Evidence summaries | Assumptions, Tasks, existing Discoveries, decisions, stale state, caches | helper **Implemented**; no protected call site |
| generic Discovery Synthesis Context | same summary family under a mode-specific policy | existing Discoveries and planning/audit material | **Known deviation** in naming; isolated by architecture tests |
| Protected Conclusion Context | canonical Hypothesis, accepted DataProfile metadata, complete active Evidence, provenance, method, decision rule, uncertainty, limitations, invalidators, and digests | SessionFrames, Assumptions, prior Discoveries, retrieval results, pins, chat, GeneratedViews | separate repository-built path **Implemented** |

Evaluated Hypotheses are historical workflow/test contracts. Policy excludes
them from ordinary future context by default. Their admitted Discovery is the
durable claim future planning or answering should use. The current
Discovery-only retrieval engine therefore never retrieves a completed
Hypothesis as a substitute for knowledge.

## Pinned invalid state

Consider a Discovery pinned in a frame and later invalidated because its
Evidence loses authority.

1. The pin may remain as a historical reference.
2. Repository-backed retrieval reloads the Discovery and excludes it before
   scoring.
3. The caller receives an exclusion note when the invalid pin is encountered.
4. A frame containing affected scientific references or summaries can be
   superseded by validity propagation.
5. A pin-only frame is not currently included in that affected-frame scan, so
   it may remain active-status.
6. A superseded frame cannot build a supported Planner projection, and
   repository-backed retrieval still re-reads lifecycle state, so a stale frame
   cannot restore the invalid Discovery.
7. No successor frame or user-facing conflict notice is created automatically.
8. The validity transaction owns the scientific lifecycle change; its complete
   propagation and recovery semantics are described in
   [Atomic validity propagation](../validity/validity-propagation.md) and
   [Active retrieval after invalidation](../validity/active-retrieval-after-invalidation.md).

Classification:

```text
B. SAFE BUT UNDER-ENFORCED
```

The active retrieval invariant is enforced and tested. The under-enforcement is
in frame lifecycle refresh and user experience, not permission for invalid
scientific state to become active.

## Retrieval invariant review

| Candidate invariant | Classification | Current evidence and limit |
| --- | --- | --- |
| structural admissibility precedes relevance | C. **Partially implemented** | explicit exclusions and invalid/deprecated lifecycle state precede scoring; wrong-profile state remains rankable context-only and independent scope filtering is absent |
| invalid authority cannot be restored by ranking or a pin | A. **Implemented** and tested | invalidated/deprecated Discoveries are removed even when pinned |
| wrong-profile knowledge cannot silently motivate work | B. **Implemented** but under-enforced | retrieval marks it context-only with a warning and commit revalidates; it is not removed before ranking |
| Assumption is mode-dependent | A. **Implemented** and tested | active Assumptions can guide planning and are structurally absent from protected evaluation |
| completed Hypothesis is historical | A. **Implemented** and tested for policy/projection | evaluated Hypotheses are excluded by default; the general answer product path remains partial |
| GeneratedView is not retrieval authority | A. **Implemented** as a policy/protected-schema boundary | a complete GeneratedView workflow is a **Design target** |
| historical traceability remains available | A. **Implemented** and **Verified on SQLite** | lifecycle exclusion does not delete repository history |

No supported production path passes SessionFrame-derived context to protected
evaluation, governance verification, or Discovery admission. Architecture
enforcement protects that separation.

## Why deterministic lexical retrieval is reasonable now

A bounded lexical baseline is transparent, reproducible, inspectable, and easy
to debug. It introduces little operational state and cannot hide an opaque
semantic model upstream of authority filtering.

Its limitations are real:

- weak synonym and paraphrase matching;
- limited conceptual similarity and cross-domain vocabulary;
- no multi-hop or graph-structural reasoning;
- declining recall as Discovery volume grows;
- no understanding of scope compatibility; and
- no replacement for lineage-aware Graph Miner behavior.

Future semantic, vector, hybrid, or graph ranking may improve relevance. It must
remain downstream of lifecycle, validity, epistemic-type, DataProfile, and
scope admission. An embedding score must never become a validity override.

Graph Miner, embeddings, vector retrieval, persistent semantic indexing, and
distributed retrieval are **Deferred**. The existing Graph Miner module is a
stub and is not registered as a runtime retrieval capability.

## Scaling and revisit triggers

Revisit the current design when Discovery volume makes the recent relational
window insufficient, terminology variation materially reduces recall,
multi-hop relationships become necessary, several active DataProfiles require
explicit comparison, or users need larger explainable retrieval traces.

A future design may add indexes, graph traversal, hybrid ranking, or cached
features. It must preserve:

- repository-current lifecycle authority;
- explicit profile and scope isolation;
- mode-specific epistemic admissibility;
- user exclusions without validity mutation;
- pins that cannot restore invalid state; and
- deterministic, reviewable inclusion reasons.

## Implementation orientation

The policy, planning retrieval engine, lexical scorer, and SessionFrame
projection are under `src/memory/`. Request and result contracts are under
`src/schemas/retrieval.py`. Discovery and Task candidates come from their
repositories; current Planner call sites are under `src/agents/planner/`.

Focused verification is under `tests/memory/`, `tests/architecture/`,
`tests/application/`, and `tests/e2e/`.

Return to [SessionFrame and active context](session-frame.md),
continue to [Retrieval strategy](retrieval-strategy.md)
for ranking, budget, and scaling decisions, or continue to
[Context continuity and resume](continuity-and-resume.md).
