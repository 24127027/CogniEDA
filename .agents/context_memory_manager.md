# Context curation instruction

## Classification and status

This is a repository instruction for proposing bounded active context. It does
not define a canonical runtime agent, and current `main` has no end-to-end
context-manager workflow.

The canonical owner is [Context](../docs/concepts/context/index.md); current
support is in [Current state](../docs/status/current-state.md).

## Authority boundary

- Planner may coordinate a SessionFrame proposal.
- Application authority validates and persists an admitted SessionFrame.
- This instruction may propose selections and warnings; it must not mutate
  research state, declare validity, admit cross-Objective reuse, or infer
  authority from prose.
- Graph Miner may supply read-only typed references. Retrieval and similarity
  never grant admission authority.

## Required behavior

1. Resolve one exact Objective and purpose before selecting context; otherwise
   fail closed.
2. Apply type, authority, lifecycle, validity, lineage, contract, and
   permitted-use checks before relevance ranking.
3. Keep Assumptions planning-only. Exclude them and prior Discoveries from
   protected evaluation and Discovery synthesis.
4. Exclude invalid, superseded, rejected, stale, unverified, wrong-Objective,
   or incomplete-lineage state from protected use.
5. Treat SessionFrame as an FCO outside the semantic graph, never a transcript,
   GeneratedView, or scientific authority.
6. Preserve warnings, exclusions, pending work, and exact provenance without
   inventing missing links.
7. Cross-Objective Evidence reuse requires exact canonical admission; fuzzy
   relevance is insufficient.

Return a bounded proposal with Objective, purpose, mode, scope, eligible
references, provenance, exclusions, validity warnings, review obligations,
pending work, and permitted next actions. It remains a proposal until admitted
by application authority.
