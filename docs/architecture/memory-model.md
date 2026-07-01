# Memory Model

## Target Design

CogniEDA memory is validity-preserving research memory. It is not retained chat history, generic vector retrieval, or a compressed session summary.

The target memory model separates four concerns:

| Memory layer | Target role |
| --- | --- |
| Working Memory / `SessionFrame` | User-governed active context exposed to the agent. |
| Semantic Research Memory | Typed research objects and relationships, especially `Objective`, `DataProfile`, `Assumption`, `Evidence`, and `Discovery`. |
| Workflow State Memory | `Task` hierarchy, approvals, active/paused work, retries, and planning state. |
| Provenance Memory | Execution traces, tool calls, cleaning decisions, code versions, parameter choices, rejected paths, and user decisions. |
| Evidence Cache | Computation reuse keyed by data profile, analysis frame, method, parameters, code, environment, and seed. |

The target design requires typed retrieval. Relevance alone is not enough; an object with the wrong epistemic role must not enter the wrong reasoning context.

## Current Implementation

The current repository implements parts of this model:

- `SessionFrame` is persisted as an append-only snapshot with dataset summaries, active assumptions, active hypotheses, evidence summaries, recent decisions, pending task strings, warnings, stale context, dead ends, cached tool-result summaries, and invalidation rules.
- `SessionFrameBuilder` can construct a compact frame from current `Project`, `DatasetAsset`, `DataProfile`, `Assumption`, `Hypothesis`, `Evidence`, and `DecisionLog` objects.
- `SessionContextBuilder` can project a `SessionFrame` snapshot into typed `planning` and `conclusion` context bundles. Planning context may include active assumptions. Conclusion context excludes assumptions, decisions, pending tasks, stale context, dead ends, and cached tool-result summaries.
- Evidence and profile records include some provenance and invalidation metadata.
- There is no typed graph retrieval implementation.
- There is no graph-level separation between Planning Context, Execution Context, Conclusion Context, and Audit Context.
- There is no target `Discovery` object, so future-session retrieval cannot yet retrieve evidence-bound discoveries instead of completed hypotheses.

## Implementation Status

| Concept | Status | Note |
| --- | --- | --- |
| `SessionFrame` snapshots | Partially implemented | Persisted and tested, but not yet the target user-governed active context item model. |
| Semantic Research Memory | Partially implemented | Current schemas store some research artifacts, but not the final FCO set and not a graph. |
| Workflow State Memory | Not implemented | `Task` does not exist; planner state is empty. |
| Provenance Memory | Partially implemented | Evidence provenance and decision logs exist, but no `AnalysisFrame`, `ExecutionRun`, or append-only provenance ledger exists. |
| Evidence Cache | Not implemented | Only session-frame-level `ToolResultCacheSummary` exists. |
| Context Type Safety | Partially implemented | Basic `SessionFrame` projection enforces planning-vs-conclusion exclusions, but no typed graph retrieval policy exists. |

## Known Deviation

The current `SessionFrame` can include active assumptions and evidence summaries together. That is acceptable for a working context snapshot. Code now provides a conclusion-context projection that excludes assumptions, but direct prompt construction from raw `SessionFrame` snapshots would still bypass that guard.
