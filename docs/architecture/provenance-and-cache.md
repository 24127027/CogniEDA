# Provenance And Cache

## Target Design

CogniEDA separates provenance and cache from durable scientific knowledge.

Target provenance records include:

- `ObjectiveRevision`
- `PlannerOperation`
- `ExecutionRun`
- `AnalysisFrame`
- rejected paths
- cleaning decisions
- tool calls
- notebook executions
- method parameters
- code versions
- user decisions
- raw interaction traces when needed for audit

Target cache is an evidence-cache index keyed by:

- hypothesis signature hash
- `DataProfile`
- `AnalysisFrame` hash
- method ID
- parameter hash
- code version
- environment hash
- random seed where applicable

Cache can reuse Evidence, but it must not create Discovery by itself.

## Current Implementation

Current provenance exists in typed but incomplete forms:

- `Evidence` requires `analysis_frame_ref`, `execution_run_ref`, code/environment references where available, parameters, artifact refs, and result payload.
- `Discovery.validity_basis` records evidence, data profile, analysis frame refs, method, parameters, code/environment identity, decision rule, uncertainty, assumptions-excluded flag, and invalidators.
- `UserDecision` persists typed user-decision provenance.
- `DataProfile.preprocessing_history` records transformation steps.
- `SessionFrame` can store stale context markers, dead ends, cached tool results, and invalidation rules.

Dedicated `AnalysisFrame`, `ExecutionRun`, `PlannerOperation`, and cache tables are not implemented.

## Implementation Status

| Concept | Status | Current implementation note |
| --- | --- | --- |
| `AnalysisFrame` | Partially implemented | Evidence and Discovery validity use references; no full analytical-view record exists. |
| `ExecutionRun` | Partially implemented | Evidence and executor output use references; no execution-attempt provenance record exists. |
| `PlannerOperation` | Partially implemented | Planner contracts expose operation identifiers; no schema/table/repository exists. |
| `ObjectiveRevision` | Not implemented | Objective changes update the current Objective; revision provenance is missing. |
| Evidence provenance | Implemented locally | Required fields exist, but referenced provenance records are not persisted. |
| Cleaning provenance | Partially implemented | DataProfile preprocessing history exists; no full cleaning decision ledger exists. |
| Evidence cache | Not implemented | `ToolResultCacheSummary` is a session-frame summary, not a cache service. |

## Architectural Risk

Until full `AnalysisFrame` and `ExecutionRun` records exist, Evidence can identify provenance references but cannot fully answer which rows, filters, missing-data policy, method version, and environment produced the result.
