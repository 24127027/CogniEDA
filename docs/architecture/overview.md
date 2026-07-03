# Architecture Overview

## Target Design

CogniEDA models analytical investigation as governed research state. The system separates research intent, workflow state, data state, assumptions, hypothesis/test contracts, observed evidence, evidence-bound discoveries, active context, provenance, and cache.

The canonical FCO set is `Objective`, `DataProfile`, `Assumption`, `Task`, `Hypothesis`, `Evidence`, `Discovery`, and `SessionFrame`.

## Current Implementation

The current implementation is a Python scaffold managed with `uv`. It contains:

- target FCO schemas in `src/schemas/artifacts.py`
- value objects and validity/provenance summaries in `src/schemas/common.py`
- SQLModel tables and SQLite setup in `src/db/`
- thin repositories in `src/repositories/`
- baseline profiling utilities and a DVC adapter boundary in `src/data/`
- `SessionFrameBuilder` and `SessionContextBuilder` in `src/memory/session_frame.py`
- planner/executor contract scaffolding in `src/agents/`
- tests for repositories, profiling semantics, DB foreign keys, and session-frame context projection

## Implementation Status

| Area | Status | Current implementation note |
| --- | --- | --- |
| Current schema layer | Implemented | Pydantic models exist for the target FCO set plus typed `UserDecision` provenance. |
| SQLModel persistence | Implemented locally | Tables exist under `src/db/models.py`; `init_db()` creates tables for the target local schema. |
| Repository layer | Implemented locally | Thin repositories exist for FCOs and `UserDecision` provenance, with local Task-to-Hypothesis and Hypothesis-to-Discovery admission guards. |
| Data profiling | Partially implemented | Baseline dataframe profiling exists and produces immutable DataProfiles with optional DVC identity. Executable DVC integration is missing. |
| Planner workflow | Partially implemented | Planner contracts and node names exist, but most nodes are stubs and operation persistence is missing. |
| Executor workflow | Partially implemented | Executor contracts can return Evidence/Discovery drafts, but executor graph bodies are stubs. |
| Context type safety | Partially implemented | `SessionContextBuilder` enforces Planning, Answer, and Discovery Synthesis filtering for `SessionFrame` snapshots; graph retrieval policy does not exist. |
| Validity basis | Implemented locally | `Discovery.validity_basis` records dependency and invalidation metadata. Full provenance records are still missing. |
| AnalysisFrame provenance | Partially implemented | Evidence requires `analysis_frame_ref`; no full `AnalysisFrame` provenance table exists. |
| Evidence cache | Not implemented | No evidence-cache service exists. |

## Known Deviation

The local SQLModel schema has converged to the target FCO set, but the repository still lacks migrations for older local database files and lacks full planner/executor/provenance runtime behavior.

See [Implementation Gap Analysis](implementation-gap-analysis.md).
