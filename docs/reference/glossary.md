# Glossary

## Concepts

| Term | Meaning | Implementation note |
| --- | --- | --- |
| `Objective` | FCO for research intent. | Implemented locally. |
| `DataProfile` | FCO for dataset-version semantic state. Immutable. | Implemented locally with dataset path and optional DVC identity. |
| `Assumption` | FCO for planning constraints or axioms. Not Evidence. | Implemented locally with source, testability, scope, contradiction refs, and replacement refs. Planner warning flow remains incomplete. |
| `Task` | FCO for workflow state and user-controlled work. | Implemented locally; planner integration remains incomplete. |
| `Hypothesis` | FCO for one atomic test contract from one terminal Task. | Implemented locally. |
| `Evidence` | FCO for observed analytical result. Not interpretation. | Implemented locally with DataProfile, AnalysisFrame, and ExecutionRun refs. |
| `Discovery` | FCO for evidence-bound claim. | Implemented locally with structured claim and `validity_basis`. |
| `SessionFrame` | FCO for active user-governed context. | Partially implemented as append-only compact snapshots. |
| `Workspace` | Filesystem/runtime boundary containing files and one independent graph database. | No Workspace FCO exists. |
| `Question` | User interface input that becomes or modifies a Task. | No Question FCO exists. |
| `AnalysisFrame` | Provenance/data-view record for exact dataframe view used in Evidence. | Minimal durable record exists and is materialized by the scientific finalizer; full reproducibility detail remains incomplete. |
| `GeneratedView` | Runtime/provenance output such as answer or synthesis. Not Discovery. | Not a durable FCO. |
| `PlannerOperation` | Pending mutation produced by planner nodes before commit. | Durable envelope/table/repository and local atomic commit/rollback boundary exist; handler/reachability gaps remain. |
| `ExecutionRun` | Provenance/workflow record for one execution attempt. | Durable attempt record exists with outbox/inbox/approval, lease, fencing and recovery metadata; full reproducibility detail remains incomplete. |
| `EvidenceCacheEntry` | Cache record keyed by data/method/parameter/code/environment identity. | Not implemented. |
| `validity_basis` | Discovery metadata describing evidence, data, method, uncertainty, excluded assumptions, and invalidators. | Implemented locally. |
| Planning Context | Context mode where assumptions may guide planning. | Implemented for SessionFrame projection; no graph retriever exists. |
| Discovery Synthesis Context | Context mode for generating a new evidence-bound Discovery; excludes assumptions, Tasks, and existing Discoveries. | Implemented for SessionFrame projection; `conclusion` remains a legacy mode name. No graph retriever exists. |
| Answer Context | Context mode for user Q&A that may include existing Discoveries. | Implemented for SessionFrame projection; not a Discovery synthesis input. |

## Current Helper Names

| Name | Role | Target-design note |
| --- | --- | --- |
| `ToolResultCacheSummary` | Cached tool-result summary embedded in `SessionFrame`. | Not target cache persistence. |
| `EvidenceProvenance` | Embedded provenance fields on Evidence. | References minimal durable AnalysisFrame and ExecutionRun records; full provenance detail remains incomplete. |
| `SessionFrameBuilder` | Deterministic builder for compact SessionFrame snapshots. | Useful scaffold; not full user-governed retrieval. |
| `SessionContextBuilder` | Non-persistent projector from `SessionFrame` snapshots into planning, answer, conclusion, or discovery-synthesis context bundles. | Partial context-type-safety guard; not a graph retriever and not an FCO. |
