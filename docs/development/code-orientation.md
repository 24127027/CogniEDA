# Code orientation

This page answers where the current implementation lives. It is not a second
definition of CogniEDA's concepts: follow the linked canonical pages for
meaning and the source/tests named here for implementation behavior.

## Responsibility map

| Responsibility | Primary package and load-bearing owner | Supporting packages | Focused tests | Canonical owner and current limitation |
| --- | --- | --- | --- | --- |
| Runtime and composition | `src/application/runtime.py`: `CogniEDARuntime`; `src/application/runtime_loader.py`: `load_runtime_from_environment` | `src/db/`, `src/tools/`, executor and Analyst packages | `tests/application/test_runtime_composition.py` | [Runtime boundary](../runtime-and-composition-boundary.md). Explicit injected adapters are required; no product bootstrap exists. |
| Planner and ordinary workflow | `src/agents/planner/`; `src/application/orchestrator/planner_commit.py`: `commit_planner_operations` | `src/schemas/planner_operations.py`, planner/research repositories | `tests/agents/planner/`, `tests/application/orchestrator/`, `tests/repositories/test_planner_operations.py` | [Planner boundary](../planner-boundary-and-operation-model.md). Direct Planner persistence composition is known debt. |
| Execution coordination | `src/application/execution/`: `ExecutionAttemptTransitionService` | `src/agents/executor/`, execution repositories and schemas | `tests/application/execution/test_transition_service.py`, execution race/recovery repository tests | [Execution-to-Discovery workflow](../from-execution-to-discovery.md). No production worker or concrete adapter. |
| Evidence admission | `src/application/evidence/admission_service.py`: `execute_evidence_admission_plan` | `src/application/execution/`, evidence repositories and schemas | `tests/application/evidence/test_evidence_admission.py`, scientific-commit race tests | [Scientific authority](../scientific-authority.md). Admission preserves observations; it does not interpret them. |
| Protected evaluation | `src/application/evaluation/`: bundle builder, runner, and `EvaluationTransitionService` | `src/agents/executor/hypothesis_analyst/`, evaluation schemas/repositories | `tests/application/evaluation/`, `tests/agents/test_hypothesis_analyst_authority.py` | [Protected evaluation context](../protected-evaluation-context.md). A generic synthesis-named SessionFrame projection remains, but is not a protected input. |
| Governance | `src/application/governance/`: `GovernanceAuthorityIssuer` and `DiscoveryAdmissionGovernanceService` | governance schemas/repositories | `tests/application/governance/`, proposal-decision race tests | [Governance and Discovery admission](../governance-and-discovery-admission.md). Product authentication resolver is deployment supplied. |
| Discovery admission | `src/application/discovery/`: `AtomicDiscoveryAdmissionService` and coordinator | evaluation, governance, research, and discovery repositories | `tests/application/discovery/`, `tests/e2e/test_research_lineage.py` | [Governance and Discovery admission](../governance-and-discovery-admission.md). Verified only on SQLite. |
| Validity propagation | `src/application/validity/`: `AtomicValidityPropagationService` | validity schemas/repository plus dependent repositories | `tests/application/validity/test_validity_propagation.py`, validity repository tests | [Atomic validity propagation](../atomic-validity-propagation.md). Relational local propagation; no distributed cutover. |
| SessionFrame and continuity | `src/memory/session_frame.py`: `SessionContextBuilder` and frame builder | research SessionFrame schema/repository | `tests/memory/test_session_frame_builder.py`, validity tests | [SessionFrame and active context](../session-frame-and-active-context.md). Latest-active selection is database-global. |
| Retrieval | `src/memory/retrieval_engine.py`: `DiscoveryRetrievalEngine` | `src/memory/retrieval_policy.py`, discovery/research repositories | `tests/memory/test_retrieval_engine.py`, `tests/memory/test_retrieval_policy.py` | [Retrieval strategy](../retrieval-strategy-and-scaling.md). Default scorer is lexical; semantic indexing and Graph Miner are deferred. |
| Schemas and lifecycle contracts | `src/schemas/`, especially `research/`, `evidence/`, `execution/`, `evaluation/`, `governance/`, `discovery/`, and `validity/` | `src/schemas/canonical.py`, `src/schemas/enums.py` | `tests/schemas/`, `tests/architecture/` | [Research-state model](../research-state-model.md). A schema is a contract, not proof of product support. |
| Repositories and physical models | `src/repositories/`; `src/db/models/` with the bounded `db.models` facade | application owners and `src/db/session.py` | `tests/repositories/`, `tests/db/test_model_import_safety.py` | [Persistence ownership](../persistence-and-transaction-ownership.md). Repositories participate in writes but do not own scientific transactions. |
| Database initialization and migrations | `src/db/init_db.py`, `src/db/migrations.py`, and `src/db/legacy_migration.py` | models and session setup | `tests/db/test_legacy_migration.py`, `tests/db/test_s3b_sqlite_schema_equivalence.py` | [Database initialization and migrations](../database-initialization-and-migrations.md). Targeted history has no immutable revision identities. |
| Tools, skills, configuration | `src/tools/`, `config/`, and `skills/` | `src/agents/llm.py` | `tests/tools/test_manager.py`, runtime and documentation-integrity tests | [Product bootstrap boundary](../product-surface-and-bootstrap-boundary.md). Checked-in MCP and skill references are unresolved. |
| Product and operational seams | `src/application/runtime.py` and `src/application/runtime_loader.py` | bootstrap README, adapters, configuration | runtime, architecture, and E2E lineage tests | [Product surface](../product-surface-and-bootstrap-boundary.md). No supported CLI, API, worker, daemon, or user journey. |

## Transaction and authority owners

Repositories map durable records; the following owners control transitions.
Their concurrency claims are **Verified on SQLite**, not portable guarantees.

| Owner | Owned transition and allowed participants | Replay or concurrency mechanism | Forbidden alternate writer | Primary tests |
| --- | --- | --- | --- | --- |
| `ExecutionAttemptTransitionService` | ExecutionRun attempt succession, approval/outbox/inbox state, claim, lease, fencing, and staged effects; execution helpers participate | compare-and-set updates, owner/token/lease/fence checks, deterministic replay/conflict checks | repositories, Planner, or an executor independently finalizing scientific state | execution transition, race, recovery, and scientific-commit race tests |
| `execute_evidence_admission_plan` | Accepted execution observations into AnalysisFrame/Evidence state; execution finalization supplies the plan | plan preconditions, atomic admission boundary, replay/conflict checks | Data Explorer interpreting output or repositories admitting a partial result | Evidence-admission and execution scientific-commit tests |
| `EvaluationTransitionService` | Evaluation control creation, claim, protected bundle lifecycle, and proposal publication | bundle/proposal digests, claims, fencing, replay/conflict checks | SessionFrame, Planner, or a repository building an unprotected scientific input | evaluation bundle, Analyst execution, and control-repository tests |
| `GovernanceAuthorityIssuer` | Exact scoped, expiring authority grant from an authenticated principal | fingerprinted scope and expiry validation | caller-supplied authority or a repository inventing a principal | governance authorization and runtime-composition tests |
| `DiscoveryAdmissionGovernanceService` | Exact proposal decision bound to authority, workspace, session, and evaluation | decision/proposal bindings, consumption and race guards | governance rewriting scientific content or directly materializing Discovery | governance authorization and proposal-decision race tests |
| `AtomicDiscoveryAdmissionService` | Exact Discovery copy, claim/evaluation commit, terminal workflow effects, decision consumption, and conclusion frame | deterministic identity, claim token/fence, CAS, exact replay, rollback, SQLite writer serialization | Planner, governance, repositories, or partial services committing any scientific subset | atomic admission, admission plan, repository guard, and E2E lineage tests |
| `AtomicValidityPropagationService` | Source authority change, dependent effects, frame freshness, and immutable ValidityEvent | server-built fingerprinted plan, CAS, exact replay, rollback, SQLite writer serialization | caller-selected effects, repositories, or a direct lifecycle update | validity propagation, validity repository, retrieval, and architecture tests |
| `commit_planner_operations` | Approved ordinary operations and guarded execution-bundle staging | approved-operation revalidation and all-or-nothing batch commit | Planner creating Evidence/Discovery, terminal scientific state, or conclusion frames | Planner, orchestrator boundary, operation repository, and architecture tests |

## Schema, repository, model, and migration navigation

These layers are intentionally different:

- `src/schemas/` defines typed domain, workflow, provenance, and command
  contracts and lifecycle validation.
- `src/repositories/` maps those contracts to guarded persistence operations.
- `src/db/models/` defines the physical SQLModel records; `db.models` is a
  bounded import facade, not ontology ownership.
- `src/db/migrations.py` and `src/db/legacy_migration.py` change existing
  database shape and quarantine legacy state during initialization.

Trace a behavior from its schema to repository/model and then to its
application owner. Do not use the physical package layout to rename the eight
FCOs or to infer scientific authority.

## Patterns not to copy

Current source contains documented deviations, not precedents: Planner direct
session/repository composition; a generic synthesis-named SessionFrame mode;
database-global latest-frame selection; active predecessors remaining active;
pin-only frame freshness; wrong-profile result budget consumption; unused
Objective and SessionFrame retrieval bindings; missing operation-scope
admission; existing-Hypothesis reuse failure; stranded approved execution
approval; Objective succession through global latest; stale Planner route
labels; semantic naming for lexical behavior; migrations without immutable
revision identities; selective database-level payload immutability; and
unresolved MCP/skill configuration. Their status and remediation triggers are
owned by the [current state](../current-state.md),
[capability map](../capability-and-maturity-map.md), and [roadmap](../roadmap.md).

Do not copy a deviation simply because a focused test documents it. Tests may
describe current behavior while the roadmap identifies its replacement boundary.
