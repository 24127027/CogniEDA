# CogniEDA Master Development Roadmap

> **Status**: `[Implemented]` (Structural Foundation S1–S4) / `[Design Target]` (Package 7 Product Slice)

This document is the **single canonical roadmap** for CogniEDA. It records completed structural packages and outlines future product vertical slices.

---

## 1. Completed Structural Foundation (S1 – S4)

The structural foundation established the governed bounded contexts, specialist authority boundaries, transaction integrity, and SQLite persistence layer.

### Gate 0 — Scientific Safety & Baseline Infrastructure `[Implemented]`
- Established core FCO schemas and initial SQLite database initialization.
- Wave 1 Integration tag: `wave-1-sqlite-integration` (`9b46c204eb4eed85c39b726bdce105ac5eac74a7`).

### Package S1-A — Data Explorer Boundary & Runtime Facade `[Implemented]`
- Isolated Data Explorer execution capabilities.
- Removed generic executor aliases and unified runtime interfaces.

### Package S1-B — Execution & Evidence Bounded-Context Decomposition `[Implemented]`
- Decomposed `application.execution` and `application.evidence`.
- Extracted `ExecutionTransitionService` and strict Evidence admission.

### Package S2-A — Evaluation & Governance Bounded-Context Decomposition `[Implemented]`
- Decomposed `application.evaluation` and `application.governance`.
- Isolated `HypothesisAnalyst` proposal authoring from governance decision recording.

### Package S2-B — Discovery & Validity Bounded-Context Decomposition `[Implemented]`
- Decomposed `application.discovery` and `application.validity`.
- Established `AtomicDiscoveryAdmissionService` and `AtomicValidityPropagationService`.

### Package S3-A — Research, Execution & Evidence Persistence Normalization `[Implemented]`
- Normalized SQLModel table models, repository boundaries, and private staging hooks for research, execution, and evidence contexts.

### Package S3-B — Evaluation, Governance, Discovery & Validity Persistence Normalization `[Implemented]`
- Normalized persistence models and trigger guards across evaluation, governance, discovery, and validity contexts.
- Verified 21 SQLModel tables, 214 `sqlite_master` objects, and 10 SQLite triggers.

### Package S4 — Canonical Documentation Reconstruction & Structural Exit Checkpoint `[Implemented]`
- Reconstructed canonical documentation hierarchy (`docs/index.md`, `project-purpose.md`, `roadmap.md`, `architecture/*`, `workflows/*`, `decisions/*`).
- Verified complete S1–S3 bounded-context structure.
- Classified Planner persistence access and verified Package 7 readiness exit criteria.

---

## 2. Next Supported Product Vertical Slice (Package 7)

Package 7 will deliver the first end-to-end user-facing analytical product slice over the verified structural foundation.

### Package 7A — Interactive Task & Hypothesis Guidance `[Design Target]`
- **Purpose**: Interactive UI/CLI workflow for research objective formulation, task decomposition, and hypothesis binding.
- **Prerequisites**: Package S4 completion.
- **Exclusions**: Unsafe auto-execution without user governance.

### Package 7B — Governed Analytical Execution Engine `[Design Target]`
- **Purpose**: Production executor dispatch, deterministic sandbox execution, and structured observation parsing.
- **Prerequisites**: Package 7A.
- **Exclusions**: Arbitrary unconstrained code execution.

### Package 7C — Synthesis & Discovery Materialization `[Design Target]`
- **Purpose**: Hypothesis evaluation bundling, proposal authoring by Hypothesis Analyst, user decision workflow, and atomic discovery materialization.
- **Prerequisites**: Package 7B.
- **Exclusions**: Automatic discovery creation bypassing user governance.

### Package 7D — Active Session Resume & Graph Visualization `[Design Target]`
- **Purpose**: Multi-session workspace resumption, interactive lineage visualization, and active retrieval context management.
- **Prerequisites**: Package 7C.
- **Exclusions**: Unchecked long-memory chat summaries.

---

## 3. Future Research & Product Packages `[Deferred]`

- **Graph Miner Context Retrieval**: Advanced graph store indexing for discovery lineage `[Deferred]`.
- **DVC / Artifact Storage Integration**: External large-scale binary dataset versioning `[Deferred]`.
- **Multi-Tenant HTTP Service & Worker Daemon**: Production HTTP/gRPC server and async worker pool `[Deferred]`.
