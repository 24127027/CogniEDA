# Context

Context is typed input available to one current operation. Planner context has
a non-subtractable base: every object retained in SessionFrame. Other
purpose-specific inputs are constructed for an Objective, reasoning mode,
scope, lifecycle point, validity basis, and authority boundary. These concepts
must not be collapsed into one universal context.

This track defines the **target design** for active context and continuity. It
does not claim that the current runtime implements every mode or recovery path.

## Active-context mental model

```text
SessionFrame -> resolve every retained member -> PlannerContext base
authorized state -> eligibility -> optional ranked supplemental context
PlannerContext base + supplemental context -> Planner visibility
authorized state -> purpose-specific closed input -> protected operation
```

Context selection does not transfer authority. An Assumption remains planning-
only when selected for planning. Evidence remains authoritative only through
its admitted scientific lineage. A Discovery remains an admitted claim rather
than becoming a premise for a new protected evaluation. A GeneratedView
remains presentation.

## SessionFrame

`SessionFrame` is the FCO that records structured research-session membership
and active selectors. It is outside the semantic Knowledge Graph, whose
membership remains exactly Objective, Hypothesis, Evidence, and Discovery.

A SessionFrame is not conversation history, a chat summary, a vector-search
result, a GeneratedView, a semantic graph node, scientific authority, or
universal memory. It is user-governed Planner context membership. Context
construction resolves every retained member and may add authorized supplemental
material; it may not silently omit, rank away, or truncate the retained base.
Visible objects retain their own type, lifecycle, validity, scope, and authority.

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

Purpose-specific use and supplemental selection consider epistemic type,
authority, lifecycle, Objective
scope, DataProfile scope, scientific lineage, validity, reasoning mode,
permitted use, freshness, and explicit exclusions. Only candidates that pass
those checks may be ranked for relevance. This ordering never removes a
SessionFrame member from Planner visibility.

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

- [SessionFrame](session-frame.md) owns structured session membership, active
  selectors, continuity, and non-authority.
- [Context type safety](context-type-safety.md) owns mode-specific eligibility
  and exclusion rules.
- [Retrieval strategy](retrieval-strategy.md) owns eligibility-first retrieval,
  Graph Miner, ranking, and fail-closed behavior.
- [Continuity and resume](continuity-and-resume.md) owns reconstruction,
  concurrency, restart, replay, leases, fencing, and pending work.
- [Validity](../validity/index.md) owns historical truth and current-use
  eligibility.

## Implementation status

**Partially implemented.** Current source has a bounded materialized
`SessionFrame` with one optional Objective, ordered Assumptions, Tasks,
Evidence, and Discovery, and one optional DataProfile. The in-process
application passes those objects without filtering into an immutable
`PlannerContext` and separately retains native conversation history for later
request understanding. Planner returns a bounded Objective proposal or exact-
text Assumption assessment; Application alone applies allowed results to its
successor SessionFrame.

The current frame is not the canonical typed-reference membership model and is
not durably restored by the runtime. Mode-specific context eligibility, exact
Objective-bound session ownership, validity-aware recovery, and end-to-end
resume orchestration and supplemental retrieval remain **Deferred**. The
superseded donor retrieval package has been removed rather than treated as a
supported context capability.
