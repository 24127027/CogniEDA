# Implementation Gap Analysis

> **Current implementation snapshot:** 2026-07-17 working tree at committed HEAD `1a586ca7561a82dee4a76d1b10d54d0b78a9d7ad`, including the reviewed uncommitted Steps 3.5A-10 changes.
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
| Planner operations | Nodes produce pending operations; approved operations commit atomically | Durable `PlannerOperation`, normal commit and special atomic execution bundle exist. Governed root motivation through `/manage_task`, `/decompose <parent-task-uuid>`, and `/objective` persist exact pending batches before approval, and only the restored, session-bound ordered batch can commit. | Partial | `DELETE_TASK` unsupported; plan/assumption/conflict approval remains incomplete |
| Objective lifecycle | One user-governed current research intent with traceable revisions | At most one `ACTIVE` Objective is database-enforced; public create/update/switch/reactivation is exact-batch approval-gated; explicit transitions, optimistic version checks, global unfinished-Task policy, atomic successor SessionFrame, and immutable non-FCO revisions are implemented | Implemented locally | `PAUSED` is compatibility-only; no history UI; direct import/repair bypasses remain intentionally explicit; databases with ambiguous active rows or malformed legacy revisions require manual repair |
| Planner request understanding | Natural language and explicit commands route deterministically | Explicit commands bypass classification; configured request-only adapter uses the LLM factory contract and returns controlled invalid results on invalid output or model failure | Partially implemented | Contextual grounding and most downstream capability nodes remain scaffold-level; live model credentials/service are required outside tests |
| Planner execution admission | User approves a revalidated execution contract before dispatch | Durable `ExecutionApproval`; approved path commits Hypothesis/Run/Outbox | Implemented narrow path | Task/decomposition/Objective approval is also end-to-end, but plan/assumption/conflict approval remains incomplete |
| Durable attempt protocol | Worker claims, renews, receives, finalizes, cancels and recovers with fencing | Transition service, outbox/inbox, lease/epoch/version, finalization fencing and reconciler exist; retry creates a successor attempt under the existing Hypothesis | Implemented locally | No process bootstrap; external side effects remain at-least-once |
| Scientific finalization | Executor observations become Evidence/Discovery only through deterministic admission | One deterministic-test processor validates contract and creates AnalysisFrame/Evidence/Discovery/lifecycle/SessionFrame operations | Implemented narrow method | No generic method registry, effect-size/sample-size policy, multiple testing or full diagnostics |
| Executor capability dispatch | Durable attempts reach one registered domain executor without weakening attempt ownership | Worker validates run/outbox/FCO identity, binds UUIDs, and reaches one `ExecutorInput` adapter plus lazy registry; receiver/finalizer remain separate | Partial | Default GraphMiner/HypothesisAnalyst graph builders raise `NotImplementedError`; `data_exploration` and production worker bootstrap are absent |
| Context type safety | Planning may use Assumptions; synthesis must exclude them and existing Discoveries | Pure `RetrievalPolicy`, local planning/synthesis/answer projections, and bounded structural-plus-lexical Discovery retrieval for governed root motivation and `/decompose` exist | Partial | No vector/embedding retrieval, historical-review mode, complete indexed search, cache, or production prompt assembly |
| SessionFrame | Durable scoped active-context/checkpoint artifact | Append-only repository, builder and scientific finalizer snapshot exist; approved root Task motivation, decomposition, and Objective lifecycle batches append successor snapshots | Partial | Planner does not automatically refresh/pin/prune/synchronize frames outside those narrow approved paths |
| Data versioning | Physical versions plus immutable DataProfiles and explicit transformation lineage | CSV/Parquet loading and baseline profiler exist; DVC boundary is explicit | Partial | DVC methods are not implemented; no cleaning/derived-version workflow |
| Evidence cache | Validity-keyed optimization that cannot author Discovery | No cache record/service | Not implemented | Key design, invalidation and runtime integration remain target-only |
| Product surface | User-facing CLI/service and independent worker loop | No production entrypoint | Not implemented | Current modules require external bootstrap/injected executor |
| End-to-end lineage proof | D1/D2 motivate governed T0 decomposition; executable T3 reaches H3/retry/E3/D3 without epistemic leakage | One integration test uses public approved T0 motivation, public approved typed decomposition, public execution admission, real retry/adapter/receiver/finalizer boundaries, and repository lineage reads | Implemented locally | This is not a production product loop; executor implementation is a permitted deterministic test adapter |
| Quality gates | Tests, lint and strict type checks pass in CI | Local Python pytest passes 279 tests; the focused Step 3.5A-10 regression union passes 211 tests; Ruff passes on every Step 10-touched source/test file; focused mypy reports 109 existing dependency/type errors in five files; no tracked CI workflow | Partial / failing gates | Global mypy and production integration readiness remain unresolved |

## Reviewed boundaries

### Step 3.5B: execution-attempt correctness (implemented narrow scope)

Technical retry preserves Task/DataProfile/Hypothesis identity, creates a new `ExecutionRun` plus outbox from the persisted predecessor contract, and records predecessor lineage. A unique direct-successor constraint makes a retry chain deterministic under concurrent authorization. A retry of a failed successor must target that successor rather than fork the original attempt.

### Step 10: local lineage proof implemented

`/manage_task` obtains a bounded same-profile Discovery candidate set, exposes only local
references, and atomically commits a motivated root Task plus successor SessionFrame.
`/decompose` can author the typed current deterministic analytical contract without a
model-authored UUID or duplicate specification dictionary. Commit revalidates lifecycle,
profile compatibility, accepted active profile state, and analytical contract integrity.
The genuine integration proof and its permitted adapters are documented in

The review also retains the UUID-to-UUID comparison correction in
`DiscoveryRetrievalEngine` that makes valid same-profile Discoveries eligible for
motivation.

Execution admission validates duplicate operation IDs, one matching run/outbox pair, common session, immutable identifiers, admitted status, and persisted Task/Hypothesis compatibility before staging the pair. Staged `commit=False` operations are not reported as committed before their enclosing transaction commits.

### Remaining planner approval limitation

Task/decomposition/Objective proposals persist as pending `PlannerOperation` records and are resumed only when the caller supplies the matching proposal fingerprint and exact ordered operation-id list for the same session. The remaining plan/assumption/conflict approval routes are still not public workflows.

Evidence: `src/agents/planner/nodes.py`; `src/agents/planner/agent.py`; `src/agents/planner/graph.py`.

## Step status

Steps 1-3, Step 3.5A, and the narrow Step 3.5B execution-attempt correction are complete for the currently implemented scope. Step 4 remains a narrow approval-gated `/decompose <parent-task-uuid>` path. Step 5 remains partial: a typed bounded structural-plus-lexical engine now supports governed root motivation and decomposition, filters lifecycle/profile ineligibility, ranks deterministically, separates context from motivation, exposes local-reference explanations, and revalidates selections at commit. Steps 6-7 define and locally implement one durable-worker-to-domain executor contract. Steps 8-9 implement the narrow governed Objective lifecycle and retain `ObjectiveRevision` as non-FCO provenance. Step 10 is complete as a local integration proof joining governed root motivation, typed execution-ready decomposition, execution admission, retry, receiver, finalizer, and lineage reads. No default executor graph or production bootstrap is runnable. This is not semantic/vector retrieval, Objective graph traversal, a historical-review retrieval mode, autonomous general planning, or a broader product workflow.

## Verified commands

| Command class | Result |
| --- | --- |
| Full pytest | `279 passed in 48.60s` (final run) |
| Focused Step 3.5A-10 regression union | `211 passed in 18.28s` |
| Focused Step 10 guards | `7 passed in 5.92s` (final run) |
| Ruff on all Step 10-touched source and tests | Passed |
| Focused mypy | Failed with 109 existing dependency/type errors in five files: migration `__table__`, transition-service SQLModel/SQLAlchemy, registry/decorator scaffold, finalizer nullable identity, and existing Planner placeholder/type errors; no new Step 10 contract/schema/commit/retrieval error |
| `git diff --check` | Passed |

These results are not interchangeable: passing tests validate covered behavior, while failing lint/type gates remain real implementation debt.

## Owner decisions required

1. Define a scientifically governed rerun path for changed analytical contracts; technical retry intentionally reuses the existing contract and Hypothesis.
2. Define the public approval behavior for plan/assumption/conflict workflows beyond the implemented Task/decomposition/Objective batches.
3. Decide the supported migration policy for local databases created before current unique constraints and attempt columns.
4. Decide whether SQLModel/SQLite remains the durable runtime store or is a convergence layer before a graph store.
5. Define the minimum runnable executor and product bootstrap required before describing CogniEDA as an end-to-end product rather than a local integration proof.
6. Define when Ruff/mypy/CI become release gates.
