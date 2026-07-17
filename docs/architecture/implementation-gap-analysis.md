# Implementation Gap Analysis

> **Current implementation snapshot:** 2026-07-17 working tree at committed HEAD `5fb197f326b9240902004fff832ee912f6a7e934`, including the reviewed uncommitted Steps 3.5A-7 changes.
> Code is the source of truth for current behavior. This page separates implemented local contracts from target product behavior.

## Current implementation versus target

| Concept | Target design | Current implementation | Status | Remaining gap/risk |
| --- | --- | --- | --- | --- |
| FCO ontology | Exactly `Objective`, `DataProfile`, `Assumption`, `Task`, `Hypothesis`, `Evidence`, `Discovery`, `SessionFrame` | Schema, SQLModel records and repositories use exactly this FCO set | Implemented locally | No graph-store ontology runtime |
| Workspace boundary | Workspace is filesystem/runtime scope with isolated durable state | SQLite URL defaults to `.local/cognieda_graph.sqlite3`; tests cover URL isolation | Partial | No workspace registry, initializer command or service boundary |
| Immutable knowledge | `DataProfile` and `Evidence` are immutable; Discovery remains evidence-bound | Frozen schemas, append/supersede/invalidate repositories and Discovery admission guards exist | Implemented locally | Supersession/review propagation uses multiple commits and is not atomic end-to-end |
| Task/Hypothesis cardinality | Only active leaf analytical Tasks execute; one Task produces one Hypothesis | Repository admission guards, fresh-schema unique constraint on `hypotheses.task_id`, and technical retry reuse the same Hypothesis | Implemented locally | No governed changed-analysis rerun path |
| Hypothesis/Discovery cardinality | One Hypothesis produces one evidence-bound Discovery | Repository guards and fresh-schema unique constraint on `discoveries.hypothesis_id` | Implemented locally | No migration framework for arbitrary older schemas; no review UI |
| Provenance | Evidence traces DataProfile, AnalysisFrame, ExecutionRun, method, parameters and artifacts | Minimal durable `AnalysisFrame`/`ExecutionRun`; strict Evidence dereference is optional | Partial | Full reproducibility envelope, environment/code identity and artifact integrity are incomplete |
| Planner operations | Nodes produce pending operations; approved operations commit atomically | Durable `PlannerOperation`, normal commit and special atomic execution bundle exist. `/manage_task` and `/decompose <parent-task-uuid>` persist exact pending task-operation batches before approval, and only the restored, session-bound batch can commit. | Partial | `DELETE_TASK` unsupported; plan/objective/assumption/conflict approval remains incomplete |
| Planner request understanding | Natural language and explicit commands route deterministically | Explicit commands bypass classification; configured request-only adapter uses the LLM factory contract and returns controlled invalid results on invalid output or model failure | Partially implemented | Contextual grounding and most downstream capability nodes remain scaffold-level; live model credentials/service are required outside tests |
| Planner execution admission | User approves a revalidated execution contract before dispatch | Durable `ExecutionApproval`; approved path commits Hypothesis/Run/Outbox | Implemented narrow path | Task-operation approval is also end-to-end, but plan/objective/assumption/conflict approval remains incomplete |
| Durable attempt protocol | Worker claims, renews, receives, finalizes, cancels and recovers with fencing | Transition service, outbox/inbox, lease/epoch/version, finalization fencing and reconciler exist; retry creates a successor attempt under the existing Hypothesis | Implemented locally | No process bootstrap; external side effects remain at-least-once |
| Scientific finalization | Executor observations become Evidence/Discovery only through deterministic admission | One deterministic-test processor validates contract and creates AnalysisFrame/Evidence/Discovery/lifecycle/SessionFrame operations | Implemented narrow method | No generic method registry, effect-size/sample-size policy, multiple testing or full diagnostics |
| Executor capability dispatch | Durable attempts reach one registered domain executor without weakening attempt ownership | Worker validates run/outbox/FCO identity, binds UUIDs, and reaches one `ExecutorInput` adapter plus lazy registry; receiver/finalizer remain separate | Partial | Default GraphMiner/HypothesisAnalyst graph builders raise `NotImplementedError`; `data_exploration` and production worker bootstrap are absent |
| Context type safety | Planning may use Assumptions; synthesis must exclude them and existing Discoveries | Pure `RetrievalPolicy`, local planning/synthesis/answer projections, and a bounded structural-plus-lexical Discovery retrieval path for `/decompose` exist | Partial | No vector/embedding retrieval, historical-review mode, complete indexed search, cache, or production prompt assembly |
| SessionFrame | Durable scoped active-context/checkpoint artifact | Append-only repository, builder and scientific finalizer snapshot exist; approved decomposition appends a child-task projection snapshot | Partial | Planner does not automatically refresh/pin/prune/synchronize frames outside that narrow approved decomposition path |
| Data versioning | Physical versions plus immutable DataProfiles and explicit transformation lineage | CSV/Parquet loading and baseline profiler exist; DVC boundary is explicit | Partial | DVC methods are not implemented; no cleaning/derived-version workflow |
| Evidence cache | Validity-keyed optimization that cannot author Discovery | No cache record/service | Not implemented | Key design, invalidation and runtime integration remain target-only |
| Product surface | User-facing CLI/service and independent worker loop | No production entrypoint | Not implemented | Current modules require external bootstrap/injected executor |
| Quality gates | Tests, lint and strict type checks pass in CI | `uv run --no-sync pytest -q` passes 240 tests; Ruff passes on Step 7 source/test files except one pre-existing long line in `test_artifact_repositories.py`; focused mypy remains blocked by existing SQLModel/SQLAlchemy and registry typing debt; no tracked CI workflow | Partial / failing gates | Global Ruff/mypy and production integration readiness remain unresolved |

## Confirmed blockers

### Step 3.5B: execution-attempt correctness (implemented narrow scope)

Technical retry preserves Task/DataProfile/Hypothesis identity, creates a new `ExecutionRun` plus outbox from the persisted predecessor contract, and records predecessor lineage. A unique direct-successor constraint makes a retry chain deterministic under concurrent authorization. A retry of a failed successor must target that successor rather than fork the original attempt.

Execution admission validates duplicate operation IDs, one matching run/outbox pair, common session, immutable identifiers, admitted status, and persisted Task/Hypothesis compatibility before staging the pair. Staged `commit=False` operations are not reported as committed before their enclosing transaction commits.

### Remaining planner approval limitation

Task-operation proposals now persist as pending `PlannerOperation` records and are resumed only when the caller supplies the matching proposal fingerprint and exact operation-id list for the same session. The remaining plan/objective/assumption/conflict approval routes are still not public workflows.

Evidence: `src/agents/planner/nodes.py`; `src/agents/planner/agent.py`; `src/agents/planner/graph.py`.

## Step status

Steps 1-3, Step 3.5A, and the narrow Step 3.5B execution-attempt correction are complete for the currently implemented scope. Step 4 is partially implemented as an approval-gated `/decompose <parent-task-uuid>` path. Step 5 is partially implemented within that path: an active Objective and DataProfile are required, a typed retrieval engine collects structural candidates plus a bounded lexical fallback, filters lifecycle/profile ineligibility, ranks deterministically under a strict budget, exposes local-reference explanations, and revalidates selected active motivation at commit. Steps 6-7 now define and locally implement one durable-worker-to-domain executor contract, but no default graph or production bootstrap is runnable. This is not semantic/vector retrieval, Objective graph traversal, a historical-review retrieval mode, autonomous general planning, or a broader product workflow. See [Step 5 Retrieval Review](step-5-discovery-retrieval-review.md), [Step 6 Investigation](step-6-executor-contract-investigation.md), and [Step 7 Normalization](step-7-executor-contract-normalization.md).

## Verified commands

| Command class | Result |
| --- | --- |
| Full pytest | `240 passed` |
| Steps 3.5A-7 regression union | `152 passed` |
| Ruff on Step 7 source and tests | Passed except one pre-existing `E501` at `tests/repositories/test_artifact_repositories.py:825` |
| Focused mypy | New adapter/reconstruction code has no reported error; 82 existing migration, transition/receiver and dynamic-registry errors remain |

These results are not interchangeable: passing tests validate covered behavior, while failing lint/type gates remain real implementation debt.

## Owner decisions required

1. Define a scientifically governed rerun path for changed analytical contracts; technical retry intentionally reuses the existing contract and Hypothesis.
2. Define the public approval behavior for plan/objective/assumption/conflict workflows beyond the implemented Task-operation batch.
3. Decide the supported migration policy for local databases created before current unique constraints and attempt columns.
4. Decide whether SQLModel/SQLite remains the durable runtime store or is a convergence layer before a graph store.
5. Define the minimum runnable executor and product bootstrap required before describing CogniEDA as end-to-end.
6. Define when Ruff/mypy/CI become release gates.
