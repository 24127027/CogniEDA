# Implementation Gap Analysis

> **Current implementation snapshot:** 2026-07-16 at `7779d518e511afe1844f0d6a6e9b18235ed8a4d4`.
> Code is the source of truth for current behavior. This page separates implemented local contracts from target product behavior.

## Current implementation versus target

| Concept | Target design | Current implementation | Status | Remaining gap/risk |
| --- | --- | --- | --- | --- |
| FCO ontology | Exactly `Objective`, `DataProfile`, `Assumption`, `Task`, `Hypothesis`, `Evidence`, `Discovery`, `SessionFrame` | Schema, SQLModel records and repositories use exactly this FCO set | Implemented locally | No graph-store ontology runtime |
| Workspace boundary | Workspace is filesystem/runtime scope with isolated durable state | SQLite URL defaults to `.local/cognieda_graph.sqlite3`; tests cover URL isolation | Partial | No workspace registry, initializer command or service boundary |
| Immutable knowledge | `DataProfile` and `Evidence` are immutable; Discovery remains evidence-bound | Frozen schemas, append/supersede/invalidate repositories and Discovery admission guards exist | Implemented locally | Supersession/review propagation uses multiple commits and is not atomic end-to-end |
| Task/Hypothesis cardinality | Only active leaf analytical Tasks execute; one Task produces one Hypothesis | Repository admission guards and fresh-schema unique constraint on `hypotheses.task_id` | Implemented locally | Retry code conflicts with this invariant and currently fails |
| Hypothesis/Discovery cardinality | One Hypothesis produces one evidence-bound Discovery | Repository guards and fresh-schema unique constraint on `discoveries.hypothesis_id` | Implemented locally | No migration framework for arbitrary older schemas; no review UI |
| Provenance | Evidence traces DataProfile, AnalysisFrame, ExecutionRun, method, parameters and artifacts | Minimal durable `AnalysisFrame`/`ExecutionRun`; strict Evidence dereference is optional | Partial | Full reproducibility envelope, environment/code identity and artifact integrity are incomplete |
| Planner operations | Nodes produce pending operations; approved operations commit atomically | Durable `PlannerOperation`, normal commit and special atomic execution bundle exist | Partial | `DELETE_TASK` unsupported; orphan outbox false-success; non-execution approval flow not reachable |
| Planner request understanding | Natural language and explicit commands route deterministically | Explicit command parser works; fake-model classification tests pass | Broken for default NL path | Adapter calls `create_agent` with two missing arguments |
| Planner execution admission | User approves a revalidated execution contract before dispatch | Durable `ExecutionApproval`; approved path commits Hypothesis/Run/Outbox | Implemented narrow path | Only execution approval is end-to-end; other decision routes are declared but unreachable |
| Durable attempt protocol | Worker claims, renews, receives, finalizes, cancels and recovers with fencing | Transition service, outbox/inbox, lease/epoch/version, finalization fencing and reconciler exist | Implemented locally | `authorize_retry()` fails; no process bootstrap; external side effects remain at-least-once |
| Scientific finalization | Executor observations become Evidence/Discovery only through deterministic admission | One deterministic-test processor validates contract and creates AnalysisFrame/Evidence/Discovery/lifecycle/SessionFrame operations | Implemented narrow method | No generic method registry, effect-size/sample-size policy, multiple testing or full diagnostics |
| Executor capability dispatch | Registry selects runnable executors by capability | Capability catalog, registry and dispatcher exist | Partial | Default GraphMiner/HypothesisAnalyst graph builders raise `NotImplementedError`; `data_exploration` is unregistered |
| Context type safety | Planning may use Assumptions; synthesis must exclude them and existing Discoveries | Pure `RetrievalPolicy` and local planning/synthesis/answer projections exist | Partial | No graph/vector retrieval engine or production prompt assembly |
| SessionFrame | Durable scoped active-context/checkpoint artifact | Append-only repository, builder and scientific finalizer snapshot exist | Partial | Planner does not automatically refresh/pin/prune/synchronize frames |
| Data versioning | Physical versions plus immutable DataProfiles and explicit transformation lineage | CSV/Parquet loading and baseline profiler exist; DVC boundary is explicit | Partial | DVC methods are not implemented; no cleaning/derived-version workflow |
| Evidence cache | Validity-keyed optimization that cannot author Discovery | No cache record/service | Not implemented | Key design, invalidation and runtime integration remain target-only |
| Product surface | User-facing CLI/service and independent worker loop | No production entrypoint | Not implemented | Current modules require external bootstrap/injected executor |
| Quality gates | Tests, lint and strict type checks pass in CI | 210 pytest tests pass; Ruff has 12 errors; mypy has 132 errors; no tracked CI workflow | Partial / failing gates | Local behavioral coverage is stronger than static/integration readiness |

## Confirmed blockers

### Critical: retry contradicts the Task/Hypothesis invariant

`ExecutionAttemptTransitionService.authorize_new_attempt()` clones a Hypothesis for the old Task and stages a new run. A SQLite in-memory reproduction fails first on the new run's Hypothesis foreign key because the Hypothesis has not been flushed; flushing it would then violate `uq_hypotheses_task_id`. The target retry semantics require owner review rather than a local tactical patch.

Evidence: `src/application/orchestrator/transition_service.py:L570-L616`; `src/db/models.py:L181-L188`.

### High: default natural-language planner adapter is not callable

`_ConfiguredRequestUnderstandingModel` passes only worker/config to a factory that also requires dependency type and built-in tool declarations. Explicit slash commands and fake-model tests do not exercise this path.

Evidence: `src/agents/planner/nodes.py:L67-L77`; `src/agents/llm.py:L21-L35`.

### High: execution bundle validation is incomplete

An outbox-only approved operation enters the execution bundle, is skipped in the apply loop, and is marked committed without inserting an outbox row. Admission must require exactly one run/outbox pair before any operation is marked committed.

Evidence: `src/application/orchestrator/planner_commit.py:L160-L228`.

### High: declared non-execution approval routes are unreachable

The graph route table advertises task/plan/conflict approvals, while `route_process_decision()` can return only approved execution, clarify or cancel.

Evidence: `src/agents/planner/graph.py:L34-L41`; `src/agents/planner/nodes.py:L1009-L1016`.

## Verified commands

| Command class | Result |
| --- | --- |
| Full pytest with absolute project/rootdir | `210 passed` |
| Ruff on `src` and `tests` | Failed with 12 findings |
| Strict mypy on `src` | Failed with 132 errors in 14 files |

These results are not interchangeable: passing tests validate covered behavior, while failing lint/type gates remain real implementation debt.

## Owner decisions required

1. Define retry identity: reuse the existing Hypothesis, create a new Task, or revise the one-Task/one-Hypothesis invariant explicitly.
2. Decide whether non-execution approval routes are in the next implementation slice or should remain target-only vocabulary.
3. Decide the supported migration policy for local databases created before current unique constraints and attempt columns.
4. Decide whether SQLModel/SQLite remains the durable runtime store or is a convergence layer before a graph store.
5. Define the minimum runnable executor and product bootstrap required before describing CogniEDA as end-to-end.
6. Define when Ruff/mypy/CI become release gates.