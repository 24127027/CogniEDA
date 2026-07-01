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

Target cache is `EvidenceCacheEntry`, keyed by:

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

Current provenance exists only in embedded or adjacent forms:

- `Evidence.provenance` includes `source_profile_id`, `execution_label`, `code_reference`, and artifact paths.
- `DatasetAsset.lineage_steps` records transformation descriptions.
- `DecisionLog` persists decision records as a current artifact.
- `SessionFrame` can store stale context markers, dead ends, cached tool results, and invalidation rules.
- SQLModel relationships track links among current artifacts.

No dedicated provenance store or target provenance records were found.

## Implementation Status

| Concept | Status | Current implementation note |
| --- | --- | --- |
| `AnalysisFrame` | Not implemented | No exact analytical-view record exists. |
| `ExecutionRun` | Not implemented | No execution-attempt provenance record exists. |
| `PlannerOperation` | Not implemented | Planner node docs mention operations, but no schema/table/repository exists. |
| `ObjectiveRevision` | Not implemented | No target `Objective` exists. |
| Evidence provenance | Partially implemented | Embedded evidence provenance exists, but lacks target analysis frame, environment hash, parameter hash, and execution run identity. |
| Cleaning provenance | Partially implemented | `DatasetAsset.lineage_steps` exists; no full cleaning decision ledger exists. |
| Evidence cache | Not implemented | `ToolResultCacheSummary` is a session-frame summary, not target `EvidenceCacheEntry`. |

## Architectural Risk

Without `AnalysisFrame` and `ExecutionRun`, Evidence cannot fully answer which rows, variables, filters, missing-data policy, method version, and environment produced the result. That limits reproducibility and blocks full `ValidityEnvelope` enforcement.
