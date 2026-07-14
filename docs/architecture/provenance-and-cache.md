# Provenance And Cache

## Target Design

CogniEDA separates provenance and cache from durable scientific knowledge.

Target provenance records include:

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
- `PlannerOperation` has a minimal non-FCO schema, SQLModel table, repository, planner-node draft adapters, and a skeleton commit boundary.
- Objective lifecycle is stored directly on the `Objective` FCO. Approved `UPDATE_OBJECTIVE` PlannerOperations retain the requested mutation, approval lifecycle, commit timestamp, and resulting Objective identity; there is no dedicated ObjectiveRevision schema, table, or repository.
- `AnalysisFrame` and `ExecutionRun` now exist as minimal provenance schemas, SQLModel tables, and repositories.
- `EvidenceRepository` can optionally run strict provenance dereference validation for `AnalysisFrame` and `ExecutionRun` refs when strict mode is enabled or provenance repositories are supplied.
- `EvidenceRepository` has minimal helpers to mark Evidence superseded or invalidated without editing the observed result payload. Any `DiscoveryRepository` supplied for dependent flagging must use the exact same SQLModel session before either repository is read or mutated.
- `DiscoveryRepository` can flag dependent Discoveries for review during same-session Evidence supersession or invalidation helpers.

The implementation is intentionally skeleton-first. `PlannerOperation` and commit currently express the architectural boundary only: planner nodes produce operations, approved or not-required operations are dispatched by `commit`, and `commit` returns a structured result. Complete transaction semantics, rollback provenance, approval UX, and production operation coverage are not implemented.

`AnalysisFrame` and `ExecutionRun` are not FCOs. They are small provenance records that Evidence may reference by string identifier. Objective remains the stable-identity FCO for research intent; its `status` is its authoritative lifecycle field. Strict Evidence validation currently verifies only that referenced records exist and that cleanly available `DataProfile`/`Hypothesis` refs match; it is not full reproducibility validation.

No evidence-cache table or service is implemented.

## Implementation Status

| Concept | Status | Current implementation note |
| --- | --- | --- |
| `AnalysisFrame` | Partially implemented | Minimal non-FCO schema/table/repository exists with `data_profile_id`, frame identity, optional columns/filter description, and `created_at`; no materialized view or full reproducibility trace exists. |
| `ExecutionRun` | Partially implemented | Minimal non-FCO schema/table/repository exists with optional task/hypothesis/analysis-frame refs, executor/method/parameter identifiers, status, and `created_at`; no executor runtime exists. |
| `PlannerOperation` | Partially implemented | Minimal non-FCO operation envelope, table, repository, planner draft adapters, and commit dispatch boundary exist. |
| Objective mutation attribution | Partially implemented | `Objective.status` is authoritative current lifecycle state. Committed `UPDATE_OBJECTIVE` PlannerOperations remain attributable, but no dedicated before/after Objective snapshot or history UI exists. Existing local revision tables are not dropped automatically. |
| Evidence provenance | Partially implemented | Required fields exist and may reference minimal provenance records. Optional strict repository validation dereferences `AnalysisFrame` and `ExecutionRun` ids and checks available DataProfile/Hypothesis ownership fields. |
| Evidence lifecycle | Partially implemented | Repository helpers can mark Evidence as superseded or invalidated while preserving result payloads. Optional dependent-Discovery review flagging requires the exact same SQLModel session and rejects mismatches before mutation. This is repository-level safety, not transaction or rollback machinery. |
| Discovery review state | Partially implemented | `Discovery` records now carry lifecycle/review metadata, and `DiscoveryRepository.flag_by_evidence_change()` records Evidence supersession/invalidation review reasons without changing the claim, Evidence links, validity basis, or epistemic status. |
| Cleaning provenance | Partially implemented | DataProfile preprocessing history exists; no full cleaning decision ledger exists. |
| Evidence cache | Not implemented | `ToolResultCacheSummary` is a session-frame summary, not a cache service. |

## Architectural Risk

Until full `AnalysisFrame` and `ExecutionRun` records exist, Evidence can identify and optionally dereference provenance references but cannot fully answer which rows, filters, missing-data policy, method version, and environment produced the result. The current records are intentionally minimal skeleton anchors, not full reproducibility machinery. Objective mutation attribution comes from committed PlannerOperations rather than a dedicated revision store; it does not settle merge, transaction rollback, or review policy. Evidence lifecycle transitions now have same-session repository safety for optional Discovery flagging, not transaction or rollback guarantees; user review workflow, planner/executor propagation, and full impact analysis remain future work.
