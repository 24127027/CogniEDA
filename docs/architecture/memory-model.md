# Memory Model

## Target Design

CogniEDA memory is validity-preserving research memory. It is not retained chat history, generic vector retrieval, or a compressed session summary.

The target memory model separates:

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

- `SessionFrame` is persisted as an append-only active-context snapshot.
- `SessionFrameBuilder` can construct compact frames from Objective, DataProfile, Task, Assumption, Hypothesis, Discovery, Evidence, and UserDecision provenance objects.
- `SessionContextBuilder` projects a frame into typed planning, answer, conclusion, and discovery-synthesis bundles.
- `src/memory/retrieval_policy.py` defines a pure retrieval type-safety policy skeleton for `PLANNING`, `ANSWER`, `CONCLUSION`, and `DISCOVERY_SYNTHESIS` contexts.
- `SessionContextBuilder` now calls the policy when projecting lifecycle-bearing SessionFrame summaries. This is local projection filtering, not graph retrieval.
- `DiscoveryContextSummary` carries `DiscoveryLifecycleState`, so projection can distinguish active, flagged, invalidated, and deprecated Discoveries instead of relying only on summary memory status.
- `ContextBundle.exclusion_notes` now records projection-local diagnostics when `SessionContextBuilder` filters Discovery summaries from Planning or Answer Context. These notes are not persisted memory and do not replace a review workflow.
- Planning context may include active assumptions.
- Answer context may include existing Discoveries for user Q&A.
- Discovery-synthesis context excludes assumptions, tasks, existing Discoveries, user decisions, pending questions, stale context, dead ends, and cached tool-result summaries.
- Evidence and Discovery records include validity and provenance references.
- There is no typed graph retrieval implementation.
- There is no graph-level separation between Planning Context, Execution Context, Discovery Synthesis Context, Answer Context, and Audit Context.

## Implementation Status

| Concept | Status | Note |
| --- | --- | --- |
| `SessionFrame` snapshots | Partially implemented | Persisted and tested, but not yet the target user-governed active context item model. |
| Semantic Research Memory | Partially implemented | Target FCOs are modeled locally, but the store is SQLModel rather than graph retrieval. |
| Workflow State Memory | Partially implemented | `Task`, durable `PlannerOperation`, execution approval/outbox/inbox and local commit/rollback boundaries exist; broad planner behavior and product integration remain incomplete. |
| Provenance Memory | Partially implemented | Evidence references, UserDecision records, and minimal `AnalysisFrame`/`ExecutionRun` records exist; full provenance trace and dereference validation are missing. |
| Evidence Cache | Not implemented | Only session-frame-level `ToolResultCacheSummary` exists. |
| Context Type Safety | Partially implemented | Basic frame projection enforces planning/answer/discovery-synthesis exclusions, records projection-local Discovery exclusion notes, and a pure retrieval policy skeleton now defines lifecycle/type gates. No graph retrieval implementation exists. |

## Known Deviation

Direct prompt construction from raw `SessionFrame` snapshots would bypass the discovery-synthesis guard. Discovery generation should use `SessionContextBuilder` and future graph retrieval or prompt assembly must call `src/memory/retrieval_policy.py`.

The retrieval policy skeleton prevents wrong epistemic roles and invalid lifecycle states from entering specific context modes. Discovery lifecycle now reaches SessionFrame projection, and filtered Discovery summaries now leave local `ContextBundle.exclusion_notes` diagnostics. This is still projection filtering. It does not rank candidates, query a graph, refresh SessionFrames, build prompts, authorize cache reuse, provide user review UI, or implement an audit retrieval mode.
