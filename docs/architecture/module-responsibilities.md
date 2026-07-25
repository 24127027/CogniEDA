# Module Responsibility Matrix

> **Status**: `[Implemented]` / `[Verified on SQLite]`

This document provides the complete module-level responsibility matrix across all bounded contexts in CogniEDA.

---

## 1. Application Layer (`src/application/`)

| Module Path | Canonical Responsibilities | Forbidden Responsibilities |
| :--- | :--- | :--- |
| `application.execution` | `ExecutionTransitionService`, sandbox worker dispatch, run leases, retry handling | Evidence creation, scientific claim authoring |
| `application.evidence` | `EvidenceAdmissionService`, `AnalysisFrame` and `Evidence` creation | Execution state machine updates, hypothesis evaluation |
| `application.evaluation` | `EvaluationControlService`, Hypothesis Analyst execution runner | Governance decision recording, discovery materialization |
| `application.governance` | `ProposalDecisionService`, user authority token generation, decision recording | Claim evaluation, direct FCO mutation |
| `application.discovery` | `AtomicDiscoveryAdmissionService`, fenced discovery materialization | Proposal authoring, un-governed admission |
| `application.validity` | `AtomicValidityPropagationService`, invalidation triggering, dependent state updates | Claim creation, user governance decisions |
| `application.orchestrator` | Planner transaction commit coordination | Direct domain write operations bypassing transaction owners |

---

## 2. Schema Layer (`src/schemas/`)

| Module Path | Canonical Responsibilities | Forbidden Responsibilities |
| :--- | :--- | :--- |
| `schemas.research` | Value objects for `Objective`, `Task`, `Hypothesis`, `Assumption`, `SessionFrame` | Database connection or SQLModel table definitions |
| `schemas.execution` | Value objects for execution specifications, details, and observations | Application service imports |
| `schemas.evidence` | Value objects for evidence observations and admission payloads | Direct DB staging |
| `schemas.evaluation` | Value objects for evaluation controls and synthesis bundles | Governance decision logic |
| `schemas.governance` | Value objects for governance authorities and decisions | Discovery admission logic |
| `schemas.discovery` | Value objects for discoveries, claims, and admission contracts | Raw code execution contracts |
| `schemas.validity` | Value objects for validity events and propagation payloads | DB ORM definitions |

---

## 3. Repositories Layer (`src/repositories/`)

| Module Path | Canonical Responsibilities | Forbidden Responsibilities |
| :--- | :--- | :--- |
| `repositories.research` | Persistence adapters for `Objective`, `Task`, `Hypothesis`, `Assumption` | Application workflow decisions |
| `repositories.execution` | Persistence adapters for `ExecutionRun`, `Inbox`, `Outbox` records | Public generic lifecycle mutators |
| `repositories.evidence` | Persistence adapters for `AnalysisFrame` and `Evidence` records | Direct creation outside `EvidenceAdmissionService` |
| `repositories.evaluation` | Persistence adapter for `EvaluationControlRecord` | Public write mutators |
| `repositories.governance` | Persistence adapters for governance authorities and decisions | Direct decision bypasses |
| `repositories.discovery` | Persistence adapter for `DiscoveryRecord` and claims | Public `create()` method (raises `RuntimeError`) |
| `repositories.validity` | Persistence adapter for `ValidityEventRecord` | Public write mutators outside propagation service |
