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
- `PlannerOperation` has a durable non-FCO schema, SQLModel table, repository, planner-node draft adapters, and local atomic commit/rollback boundaries for normal and execution/scientific bundles.
- Objective lifecycle is stored directly on the mutable `Objective` FCO. Each governed update atomically appends one immutable non-FCO `ObjectiveRevision` containing exact before/after title, statement and status, deterministic changed fields, reason, actor, and the authorizing PlannerOperation or UserDecision reference.
- `AnalysisFrame` exists as minimal view provenance. `ExecutionRun` is a durable attempt record with outbox/inbox/approval, lease, fencing, retry and recovery metadata.
- `EvidenceRepository` can optionally run strict provenance dereference validation for `AnalysisFrame` and `ExecutionRun` refs when strict mode is enabled or provenance repositories are supplied.
- `EvidenceRepository` has minimal helpers to mark Evidence superseded or invalidated without editing the observed result payload. Any `DiscoveryRepository` supplied for dependent flagging must use the exact same SQLModel session before either repository is read or mutated.
- `DiscoveryRepository` can flag dependent Discoveries for review during same-session Evidence supersession or invalidation helpers.

The implementation now provides real local transaction/rollback behavior at the PlannerOperation boundary. Task, decomposition, and Objective proposals are persisted as pending batches and can be approved only by their matching, session-bound proposal fingerprint and ordered operation IDs. It remains incomplete as a product workflow: plan/assumption/conflict approval routes, some enum/payload handlers, distributed recovery, and broader approval UX remain unimplemented.

`AnalysisFrame` and `ExecutionRun` are not FCOs. They are small provenance records that Evidence may reference by string identifier. Objective remains the stable-identity FCO for research intent; its `status` is its authoritative lifecycle field. Strict Evidence validation currently verifies only that referenced records exist and that cleanly available `DataProfile`/`Hypothesis` refs match; it is not full reproducibility validation.

No evidence-cache table or service is implemented.

## Implementation Status

| Concept | Status | Current implementation note |
| --- | --- | --- |
| `AnalysisFrame` | Partially implemented | Minimal non-FCO schema/table/repository exists with `data_profile_id`, frame identity, optional columns/filter description, and `created_at`; no materialized view or full reproducibility trace exists. |
| `ExecutionRun` | Partially implemented | Durable non-FCO attempt plus outbox/inbox/approval, lease/fencing and recovery fields exist; runnable default analytical executors and full reproducibility metadata do not. |
| `PlannerOperation` | Partially implemented | Durable envelope/table/repository, planner draft adapters and atomic local commit/rollback exist; coverage and reachability are incomplete. |
| Objective mutation attribution | Implemented locally | `Objective.status` is authoritative current lifecycle state. `ObjectiveRevision` is append-only provenance, not an FCO; approved Planner mutations commit Objective, revision, successor SessionFrame, and operation states in one transaction. No history UI exists. |
| Evidence provenance | Partially implemented | Required fields exist and may reference minimal provenance records. Optional strict repository validation dereferences `AnalysisFrame` and `ExecutionRun` ids and checks available DataProfile/Hypothesis ownership fields. |
| Evidence lifecycle | Partially implemented | Repository helpers can mark Evidence as superseded or invalidated while preserving result payloads. Optional dependent-Discovery review flagging requires the exact same SQLModel session and rejects mismatches before mutation. This is repository-level safety, not transaction or rollback machinery. |
| Discovery review state | Partially implemented | `Discovery` records now carry lifecycle/review metadata, and `DiscoveryRepository.flag_by_evidence_change()` records Evidence supersession/invalidation review reasons without changing the claim, Evidence links, validity basis, or epistemic status. |
| Cleaning provenance | Partially implemented | DataProfile preprocessing history exists; no full cleaning decision ledger exists. |
| Evidence cache | Not implemented | `ToolResultCacheSummary` is a session-frame summary, not a cache service. |

## Architectural Risk

Current `AnalysisFrame` and `ExecutionRun` records allow Evidence to identify and optionally dereference provenance, but they cannot fully answer which rows, filters, missing-data policy, method version, environment and artifact contents produced the result. They are durable minimal anchors, not full reproducibility machinery. Objective mutation attribution now combines the approved operation/decision with exact immutable revision history; it does not add merge or collaborative-editing policy. Evidence lifecycle transitions have same-session repository safety for optional Discovery flagging, but the multi-step propagation is not atomic; user review, retrieval integration and full impact analysis remain future work.
