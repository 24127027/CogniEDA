# Implementation Gap Analysis

This report compares the audited current implementation against the target architecture. Code is the source of truth for current behavior; the final FCO design is the source of truth for target behavior.

| Affected concept | Target design says | Current implementation appears to do | Status | Remaining risk |
| --- | --- | --- | --- | --- |
| FCO set | Only `Objective`, `DataProfile`, `Assumption`, `Task`, `Hypothesis`, `Evidence`, `Discovery`, and `SessionFrame` are FCOs. | Schemas, SQLModel tables, repositories, and tests now use that FCO set. | Implemented for local schema/persistence | Migration from older local DB files is not implemented. |
| Workspace boundary | Workspace is a filesystem/runtime boundary; each workspace owns one graph DB. | The default DB is workspace-local at `.local/cognieda_graph.sqlite3`, and tests cover isolation across separate SQLite URLs. | Partially implemented | No app-level workspace registry or initializer exists. |
| DataProfile data-version identity | Raw dataset and separate dataset-version objects are not FCOs; `DataProfile` stores dataset path, DVC identity, source metadata, profile stats, preprocessing history, and acceptance state. | `DataProfile` has `dataset_path`, optional `dvc_hash`, optional `dvc_version_label`, source fields, immutable profile summaries, lifecycle state, preprocessing history, artifacts, and `accepted_as_ground_truth`. | Implemented locally | DVC identity is caller-supplied until executable DVC integration exists. |
| User decisions | Decisions are provenance, not durable scientific knowledge. | `UserDecision` and `UserDecisionRepository` replace the old generic decision artifact name. | Partially implemented | Cleaning/user-decision provenance is typed but not yet integrated into planner commit. |
| Task lifecycle | Durable Tasks use a small lifecycle and terminal analytical readiness guards. | `Task` and `TaskRepository` exist. Proposed/rejected are not durable Task states; `Task.can_generate_hypothesis()` guards local readiness. | Partially implemented | One-task-to-one-hypothesis cardinality is not enforced with a uniqueness constraint. |
| Terminal task to hypothesis | Only active terminal analytical Tasks generate Hypotheses; one terminal Task generates exactly one Hypothesis. | `Hypothesis` requires `task_id`, `profile_id`, variables, scope, method, and evidence expectation. | Partially implemented | Repository creation still trusts callers to pass an admissible Task. |
| Evidence provenance | Evidence must reference `DataProfile`, `AnalysisFrame` provenance, method, parameters, execution run, result payload, and artifacts. | `Evidence` requires `profile_id`, `analysis_frame_ref`, `execution_run_ref`, method, parameters, provenance, result summary, and artifacts. | Implemented locally | `AnalysisFrame` and `ExecutionRun` are references, not persisted provenance records yet. |
| Discovery validity | Discovery is an evidence-bound claim with structured claim, epistemic status, scope, and validity metadata. | `Discovery` requires non-empty `evidence_ids`, `claim`, `epistemic_status`, `scope`, and `validity_basis`. `validity_basis` is dependency/invalidation metadata, not the claim condition. | Implemented locally | One-hypothesis-to-one-discovery cardinality is not enforced with a uniqueness constraint. |
| Assumption quarantine | Assumptions may guide planning but must be excluded from Conclusion Context. | `SessionContextBuilder` includes assumptions in planning context and excludes them from conclusion context. | Partially implemented | Graph retrieval policy is not implemented, so future retrieval must enforce the same rule. |
| Planner ownership | Planner produces operations and dispatches executors; it does not author Evidence or Discovery. | Planner contracts expose `planner_operations` and `executor_dispatch_ref`; they do not expose Evidence or Discovery drafts. | Partially implemented | Planner nodes are still stubs and no persisted `PlannerOperation` records exist. |
| Executor ownership | Executors operate on execution state and produce Evidence/Discovery drafts. | Hypothesis analyst executor contracts expose `evidence_drafts`, `discovery_drafts`, and `execution_run_ref`. | Partially implemented | Executor graph bodies are still stubs. |
| Evidence cache | Cache is an optimization keyed by validity inputs and cannot create Discovery. | No evidence-cache service exists. | Not implemented | Future cache work must not author Discovery. |

## Highest-Risk Remaining Gaps

1. There is no migration path for older SQLite files that contain scaffold-era tables.
2. `Task` -> `Hypothesis` and `Hypothesis` -> `Discovery` one-to-one cardinality is modeled but not enforced by database uniqueness.
3. `AnalysisFrame`, `ExecutionRun`, `PlannerOperation`, and cache records are references or contracts, not full provenance stores.
4. Context type safety is local to `SessionFrame` projection; graph retrieval still needs policy enforcement.
5. DVC integration is an explicit interface, not executable integration.

## Owner Review Needed

- Decide whether existing local databases should be migrated or discarded during this scaffold convergence.
- Decide the concrete persisted shape for `PlannerOperation`, `ExecutionRun`, `AnalysisFrame`, cleaning decisions, and rejected task proposals.
- Decide whether SQLModel remains the runtime store during convergence or whether/when a graph store is introduced.
