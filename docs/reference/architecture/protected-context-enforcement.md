# Protected context enforcement

> **Role:** Technical reference. **Canonical concept owner:**
> [Protected evaluation](../../concepts/scientific-lifecycle/protected-evaluation.md).
> **Contributor entry:** [Contributor documentation](../../development/index.md).
> **Current-state owner:** [CogniEDA current state](../../current-state.md).

> **Implementation status:** protected Hypothesis evaluation **Implemented**;
> generic SessionFrame projections **Partially implemented**; broader product
> context assembly **Deferred**.

Canonical reader explanations are
[Protected evaluation](../../concepts/scientific-lifecycle/protected-evaluation.md) for
scientific evaluation and
[Context type safety and retrieval](../../concepts/context/context-type-safety.md)
for ordinary active context.
[Active retrieval after invalidation](../../concepts/validity/active-retrieval-after-invalidation.md)
owns authority changes at the read boundary. This page retains the concise
implementer reference.

## Structurally enforced protected evaluation

`DiscoverySynthesisBundle` is a frozen, closed schema. It admits Hypothesis, accepted DataProfile
metadata, AnalysisFrame/ExecutionRun provenance, active Evidence, method metadata, decision rule,
limitations, invalidators, and digests. `build_synthesis_bundle` reconstructs those values from
repositories and checks active lifecycle and exact lineage. The Hypothesis Analyst has no tools,
message history, repository, SQL session, or generic context field.

Therefore the supported protected evaluation path structurally excludes:

- Assumptions;
- existing Discoveries;
- Tasks as inference premises;
- SessionFrames and raw chat history;
- rejected/completed workflow state;
- GeneratedViews, cache entries, retrieval scores, and arbitrary prompt bags.

## SessionFrame projections

`SessionContextBuilder` provides planning, answer, conclusion, and discovery-synthesis projections.
Planning may include active Assumptions and Tasks. Answer may include active Discoveries.
Conclusion/discovery-synthesis projections exclude Assumptions, Tasks, existing Discoveries, user
decisions, dead ends, stale context, and caches.

These projections are policy helpers, not the protected evaluator's authority. The protected
evaluator uses the repository-built bundle directly. Architecture enforcement prevents the
protected Analyst, evaluation, governance, and Discovery packages from consuming
`SessionContextBuilder` or `ContextBundle`.

## Active retrieval

`DiscoveryRetrievalEngine` performs bounded SQL-backed Discovery retrieval for planning. It excludes
invalidated and deprecated Discoveries even when pinned; flagged or cross-profile results cannot
motivate a Task. Cross-profile results may remain warned context-only candidates, and an independent
operation-scope filter is not implemented. `AtomicValidityPropagationService` invalidates dependent
state and marks affected SessionFrames superseded. `SessionFrameRepository.get_latest_active`
excludes superseded frames.

## Known limitations

**Known deviation:** The general retrieval policy accepts some provenance references by string type
and has no explicit historical/audit context mode.

**Partially implemented:** SessionFrames are stored snapshots; there is no supported session-resume
UI, item-level governance workflow, or general automatic context refresh.
