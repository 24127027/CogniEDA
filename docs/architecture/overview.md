# Architecture Overview

## Target Design

CogniEDA models analytical investigation as governed research state. The target system separates:

- research intent
- workflow state
- data state
- assumptions
- hypothesis/test contracts
- observed evidence
- evidence-bound discoveries
- active context
- provenance
- cache

The canonical target FCO set is `Objective`, `DataProfile`, `Assumption`, `Task`, `Hypothesis`, `Evidence`, `Discovery`, and `SessionFrame`.

## Current Implementation

The current implementation is a Python scaffold managed with `uv`. It contains:

- Pydantic schemas in `src/schemas/`.
- SQLModel tables and SQLite setup in `src/db/`.
- artifact-specific repositories in `src/repositories/`.
- baseline profiling utilities in `src/data/`.
- `SessionFrameBuilder` and `SessionContextBuilder` in `src/memory/session_frame.py`.
- agent and planner scaffolding in `src/agents/`.
- tests for repositories, profiling semantics, DB foreign keys, and session-frame building.

The current code does not implement the full target FCO set. It uses older/current artifact names: `Project`, `DatasetAsset`, `DataProfile`, `Assumption`, `Hypothesis`, `Evidence`, `DecisionLog`, and `SessionFrame`.

## Implementation Status

| Area | Status | Current implementation note |
| --- | --- | --- |
| Current schema layer | Implemented | Pydantic models exist under `src/schemas/artifacts.py` and value objects under `src/schemas/common.py`. |
| SQLModel persistence | Implemented | Tables exist under `src/db/models.py`; `init_db()` creates tables. |
| Repository layer | Implemented | Thin CRUD/query repositories exist for current artifact classes. |
| Data profiling | Partially implemented | Baseline dataframe profiling exists; target DVC/profile acceptance lifecycle is not fully modeled. |
| Target FCO set | Partially implemented | `DataProfile`, `Assumption`, `Hypothesis`, `Evidence`, and `SessionFrame` exist in older forms. `Objective`, `Task`, and `Discovery` do not exist. |
| Planner workflow | Partially implemented | Target node names and graph routing exist, but most nodes are stubs. |
| Context type safety | Partially implemented | `SessionContextBuilder` enforces basic Planning Context vs Conclusion Context filtering for `SessionFrame` snapshots; graph retrieval policy does not exist. |
| Validity envelope | Not implemented | No `ValidityEnvelope` schema or enforcement was found. |
| AnalysisFrame provenance | Not implemented | No `AnalysisFrame` record exists. |
| Evidence cache | Not implemented | `ToolResultCacheSummary` exists inside `SessionFrame`, but target `EvidenceCacheEntry` does not. |

## Known Deviation

The largest current deviation is that the code treats `Project`, `DatasetAsset`, and `DecisionLog` as persisted artifacts, while the final target FCO design says `Objective` replaces project-level research intent, raw dataset/version identity belongs in `DataProfile`, and decisions belong in provenance rather than the FCO set.

See [Implementation Gap Analysis](implementation-gap-analysis.md).
