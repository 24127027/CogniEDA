# Architecture Overview

## Target Design

CogniEDA models analytical investigation as governed research state. The system separates research intent, workflow state, data state, assumptions, hypothesis/test contracts, observed evidence, evidence-bound discoveries, active context, provenance, and cache.

The canonical FCO set is `Objective`, `DataProfile`, `Assumption`, `Task`, `Hypothesis`, `Evidence`, `Discovery`, and `SessionFrame`.

## Current Implementation

The current implementation is a Python backend prototype managed with `uv`. It contains:

- target FCO schemas in `src/schemas/artifacts.py`
- value objects and validity/provenance summaries in `src/schemas/common.py`
- SQLModel tables and SQLite setup in `src/db/`
- thin repositories in `src/repositories/`
- baseline profiling utilities and a DVC adapter boundary in `src/data/`
- `SessionFrameBuilder` and `SessionContextBuilder` in `src/memory/session_frame.py`
- bounded SQL-backed Discovery retrieval in `src/memory/retrieval_engine.py`
- a narrow approval-gated planner admission path in `src/agents/planner/`
- a durable execution, Evidence admission, protected evaluation, Discovery governance/admission,
  and validity protocol in `src/application/orchestrator/`
- per-runtime Data Explorer registration/dispatch plumbing; a concrete Data Explorer and Graph
  Miner remain absent
- tests for planner admission, repositories, profiling, DB constraints, protected context,
  attempt races/recovery, atomic admissions, validity propagation, and retrieval exclusion

## Implementation Status

| Area | Status | Current implementation note |
| --- | --- | --- |
| Current schema layer | Implemented | Pydantic models exist for the target FCO set plus typed `UserDecision` provenance. |
| SQLModel persistence | Implemented locally | Tables exist under `src/db/models.py`; `init_db()` creates tables for the target local schema. |
| Repository layer | Implemented locally | Thin repositories exist for FCOs and `UserDecision` provenance, with local Task-to-Hypothesis and Hypothesis-to-Discovery admission guards. |
| Data profiling | Partially implemented | Baseline dataframe profiling exists and produces immutable DataProfiles with optional DVC identity. Executable DVC integration is missing. |
| Planner workflow | Partially implemented | Explicit commands and execution approval/admission work; answer/suggest/plan and general non-execution approval remain incomplete. Durable PlannerOperation persistence exists. |
| Executor workflow | Partially implemented | A per-runtime registry/dispatcher accepts only an explicitly supplied Data Explorer factory. The protected Hypothesis Analyst evaluation path is implemented; concrete Data Explorer and Graph Miner implementations are absent. |
| Context type safety | Partially implemented | A pure policy, bounded SQL-backed Discovery retrieval/ranking, and `SessionContextBuilder` projections enforce local type/lifecycle filtering. Protected evaluation uses a closed repository-built bundle; broader graph/vector retrieval is absent. |
| Validity basis | Implemented locally | `Discovery.validity_basis` records dependency and invalidation metadata. Full provenance records remain incomplete. |
| AnalysisFrame provenance | Partially implemented | Evidence requires `analysis_frame_ref`; a minimal `AnalysisFrame` table exists, but no full analytical-view provenance exists. |
| Evidence cache | Not implemented | No evidence-cache service exists. |

## Known Deviation

The local SQLModel schema has converged to the target FCO set and now includes targeted migrations
plus minimal provenance/workflow records. It still lacks a general migration framework, a concrete
Data Explorer, several Planner branches, graph/vector retrieval, cache, and a service/worker
bootstrap. No supported CLI exists. Checked-in agent tool configuration also references undefined
MCP servers. Planner still owns Hypothesis operationalization contrary to the canonical Hypothesis
Analyst responsibility.

See [Implementation Gap Analysis](implementation-gap-analysis.md).
