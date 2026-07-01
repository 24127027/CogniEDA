# Glossary

## Target Concepts

| Term | Meaning | Implementation note |
| --- | --- | --- |
| `Objective` | Target FCO for research intent. | Not implemented. Current `Project.objective` partially overlaps. |
| `DataProfile` | Target FCO for dataset-version semantic state. Immutable. | Partially implemented as current schema/repository/profiler; target fields differ. |
| `Assumption` | Target FCO for planning constraints or axioms. Not Evidence. | Partially implemented; testability admission is not enforced, and conclusion exclusion is implemented only for `SessionFrame` projection. |
| `Task` | Target FCO for workflow state and user-controlled work. | Not implemented. |
| `Hypothesis` | Target FCO for one atomic test contract from one terminal Task. | Partially implemented; no source Task or produced Discovery. |
| `Evidence` | Target FCO for observed analytical result. Not interpretation. | Partially implemented; lacks AnalysisFrame and execution-run provenance. |
| `Discovery` | Target FCO for evidence-bound claim. Requires ValidityEnvelope. | Not implemented. |
| `SessionFrame` | Target FCO for active user-governed context. | Partially implemented as append-only compact snapshots. |
| `Workspace` | Filesystem/runtime boundary containing files and one independent graph. | No Workspace model exists. |
| `Question` | User interface input that becomes or modifies a Task. | `AgentRequest.user_query` exists, but no Question FCO exists. |
| `AnalysisFrame` | Provenance/data-view record for exact dataframe view used in Evidence. | Not implemented. |
| `GeneratedView` | Runtime/provenance output such as answer or synthesis. Not Discovery. | Not implemented. |
| `PlannerOperation` | Pending mutation produced by planner nodes before commit. | Not implemented. |
| `ExecutionRun` | Provenance record for one execution attempt. | Not implemented. |
| `EvidenceCacheEntry` | Cache record keyed by data/method/parameter/code/environment identity. | Not implemented. |
| `ValidityEnvelope` | Required Discovery metadata describing scope, evidence, method, uncertainty, excluded assumptions, and invalidators. | Not implemented. |
| Planning Context | Context mode where assumptions may guide planning. | Partially implemented as a `SessionFrame` projection; no graph retriever exists. |
| Conclusion Context | Context mode for generating evidence-bound conclusions; excludes assumptions. | Partially implemented as a `SessionFrame` projection; no graph retriever exists. |

## Current Implementation Names

| Current name | Current role | Target-design note |
| --- | --- | --- |
| `Project` | Root analytical container with objective text and research questions. | Implementation deviates from target; target uses `Objective` and workspace boundary separation. |
| `DatasetAsset` | Versioned dataset reference with source, location, role, kind, and lineage. | Implementation deviates from target; target folds dataset/version identity into `DataProfile` as the data-state FCO. |
| `DecisionLog` | Persisted analytical choice and rationale. | Implementation deviates from target; target treats decisions as provenance/user-decision records, not FCOs. |
| `ToolResultCacheSummary` | Cached tool-result summary embedded in `SessionFrame`. | Not target `EvidenceCacheEntry`. |
| `EvidenceProvenance` | Embedded provenance fields on current Evidence. | Partial substitute only; target also needs `AnalysisFrame` and `ExecutionRun`. |
| `SessionFrameBuilder` | Deterministic builder for compact current SessionFrame snapshots. | Useful scaffold; not target retrieval governance. |
| `SessionContextBuilder` | Non-persistent projector from `SessionFrame` snapshots into planning or conclusion context bundles. | Partial context-type-safety guard; not a graph retriever and not an FCO. |
