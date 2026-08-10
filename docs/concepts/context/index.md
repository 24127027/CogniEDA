# Context

Context is the governed, bounded selection available to one current operation.
It is constructed for a specific Objective, purpose, reasoning mode, scope,
lifecycle point, and validity basis. It is not everything the system remembers
and not every item judged topically relevant.

This track defines the **target design** for active context and continuity. It
does not claim that the current runtime implements every mode or recovery path.

## Active-context mental model

```text
durable governed research state
  -> structural eligibility for this purpose
  -> relevance ranking among eligible candidates
  -> bounded context construction
  -> one reasoning or presentation operation
```

Context selection does not transfer authority. An Assumption remains planning-
only when selected for planning. Evidence remains authoritative only through
its admitted scientific lineage. A Discovery remains an admitted claim rather
than becoming a premise for a new protected evaluation. A GeneratedView
remains presentation.

## SessionFrame

`SessionFrame` is the FCO that records cumulative session FCO-reference history
plus governed active selectors. A separate bounded step selects run context. It
is outside the semantic Knowledge Graph, whose membership remains exactly
Objective, Hypothesis, Evidence, and Discovery.

A SessionFrame is not conversation history, a chat summary, a vector-search
result, a GeneratedView, a semantic graph node, scientific authority, or
universal memory. It selects references and bounded context; selected objects
retain their own type, lifecycle, validity, scope, and authority.

## Context modes

Different operations require different eligible types. At minimum, CogniEDA
distinguishes:

| Context purpose | Primary use | Boundary |
| --- | --- | --- |
| planning | construct or revise Objective-scoped work | may use active Assumptions and valid Discoveries for planning reference |
| planning consultation | obtain bounded Data Explorer or Graph Miner grounding | consultation output is planning support, not automatically Task, Evidence, or Discovery |
| scientific investigation control | manage feasibility, protocol, obligations, requests, and admitted lineage | scientific authority only; no Planner operationalization or direct dataset access by Hypothesis Analyst |
| protected evaluation | apply the active protocol and decision rule to a closed eligible bundle | excludes Assumptions, prior Discoveries as premises, unsafe summaries, and invalid Evidence |
| Graph Miner inquiry | locate typed references, paths, gaps, conflicts, and validity relations | read-only and no cross-Objective relation admission |
| user-facing answer or GeneratedView | summarize eligible existing state | presentation does not become Evidence or Discovery |
| recovery and resume | reconstruct durable work and permitted next actions | authority comes from typed records, never prose |
| validity review | inspect events, dependencies, eligibility, restrictions, and review obligations | historical visibility does not grant current protected-use eligibility |

These modes may share some records, but never by assuming that one universal
context is safe for all reasoning.

## Structural eligibility before relevance

Context selection considers epistemic type, authority, lifecycle, Objective
scope, DataProfile scope, scientific lineage, validity, reasoning mode,
permitted use, freshness, and explicit exclusions. Only candidates that pass
those checks may be ranked for relevance.

Semantic similarity is therefore not admission. Missing identity, scope,
lineage, or eligibility fails closed.

## Continuity without conversation replay

Continuity reconstructs governed research state. It does not replay a
conversation and ask a model to infer which statements were approved or which
results remain valid. A resumed session recovers typed identity, lifecycle,
lineage, approvals, validity, pending work, operational ownership, and
permitted next actions from durable state.

One Workspace may contain multiple concurrently active Objectives. Sessions
may work concurrently when bound to different Objectives. For the current
architecture phase, at most one active Planner session may own one Objective
at a time; this is not a one-session-per-Workspace rule.

## Continue reading

- [SessionFrame](session-frame.md) owns its identity, scope, lifecycle, and
  non-authority.
- [Context type safety](context-type-safety.md) owns mode-specific eligibility
  and exclusion rules.
- [Retrieval strategy](retrieval-strategy.md) owns eligibility-first retrieval,
  Graph Miner, ranking, and fail-closed behavior.
- [Continuity and resume](continuity-and-resume.md) owns reconstruction,
  concurrency, restart, replay, leases, fencing, and pending work.
- [Validity](../validity/index.md) owns historical truth and current-use
  eligibility.

## Implementation status

**Partially implemented.** Current source persists append-only SessionFrame
snapshots, builds bounded summaries, projects planning, answer, conclusion, and
discovery-synthesis bundles, applies a pure lifecycle/type retrieval policy,
and provides bounded planning-only Discovery retrieval with deterministic
lexical ranking.

The current SessionFrame is not explicitly bound by Objective identifier,
purpose, reasoning mode, scope, lifecycle point, or validity basis. The full
mode set, exact Objective isolation, recovery projection, Planner-session
ownership, and end-to-end resume orchestration remain target design.
