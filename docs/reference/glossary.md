# Glossary

## Concepts

| Term | Meaning | Implementation note |
| --- | --- | --- |
| `Objective` | FCO for research intent. | Implemented locally. |
| `DataProfile` | FCO for dataset-version semantic state. Immutable. | Implemented locally with dataset path and optional DVC identity. |
| `Assumption` | FCO for planning constraints or axioms. Not Evidence. | Implemented locally; admission checks remain incomplete. |
| `Task` | FCO for workflow state and user-controlled work. | Implemented locally; planner integration remains incomplete. |
| `Hypothesis` | FCO for one atomic test contract from one terminal Task. | Implemented locally. |
| `Evidence` | FCO for observed analytical result. Not interpretation. | Implemented locally with DataProfile, AnalysisFrame, and ExecutionRun refs. |
| `Discovery` | FCO for evidence-bound claim. | Implemented locally with structured claim and `validity_basis`. |
| `SessionFrame` | FCO for active user-governed context. | Partially implemented as append-only compact snapshots. |
| `Workspace` | Filesystem/runtime boundary containing files and one independent graph database. | No Workspace FCO exists. |
| `Question` | User interface input that becomes or modifies a Task. | No Question FCO exists. |
| `AnalysisFrame` | Provenance/data-view record for exact dataframe view used in Evidence. | Referenced by Evidence; full record missing. |
| `GeneratedView` | Runtime/provenance output such as answer or synthesis. Not Discovery. | Not a durable FCO. |
| `PlannerOperation` | Pending mutation produced by planner nodes before commit. | Planner contract exists; persistence missing. |
| `ExecutionRun` | Provenance record for one execution attempt. | Referenced by Evidence; full record missing. |
| `EvidenceCacheEntry` | Cache record keyed by data/method/parameter/code/environment identity. | Not implemented. |
| `validity_basis` | Discovery metadata describing evidence, data, method, uncertainty, excluded assumptions, and invalidators. | Implemented locally. |
| Planning Context | Context mode where assumptions may guide planning. | Implemented for SessionFrame projection; no graph retriever exists. |
| Conclusion Context | Context mode for generating evidence-bound conclusions; excludes assumptions. | Implemented for SessionFrame projection; no graph retriever exists. |

## Current Helper Names

| Name | Role | Target-design note |
| --- | --- | --- |
| `ToolResultCacheSummary` | Cached tool-result summary embedded in `SessionFrame`. | Not target cache persistence. |
| `EvidenceProvenance` | Embedded provenance fields on Evidence. | References AnalysisFrame and ExecutionRun; full provenance records remain missing. |
| `SessionFrameBuilder` | Deterministic builder for compact SessionFrame snapshots. | Useful scaffold; not full user-governed retrieval. |
| `SessionContextBuilder` | Non-persistent projector from `SessionFrame` snapshots into planning or conclusion context bundles. | Partial context-type-safety guard; not a graph retriever and not an FCO. |
