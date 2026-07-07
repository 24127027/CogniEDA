# Executor Dispatch — Implementation Plan

Step-by-step implementation of the capability-based executor dispatch layer. Follow phases in order; steps within a phase can run in parallel where noted.

## Phase 1: Capability Contracts

### Step 1 — Define `Capability` enum

**File**: `src/agents/executor/types.py`

Add a `Capability` StrEnum with the initial capability set:

- `GRAPH_MINING = "graph_mining"`
- `HYPOTHESIS_TESTING = "hypothesis_testing"`
- `DATA_EXPLORATION = "data_exploration"`

Use `StrEnum` (same pattern as `FirstClassObjectType` and `TaskKind` in `src/schemas/enums.py`). Import `StrEnum` from `enum`.

### Step 2 — Update `ExecutionRequest`

**File**: `src/agents/executor/types.py`

Replace `executor_name: str` with `capability: str`. The request now declares *what* is needed, not *who* should do it.

### Step 3 — Update `ExecutionResult`

**File**: `src/agents/executor/types.py`

Replace the empty `...` body with structured fields for what executors produce:

```python
class ExecutionResult(BaseModel):
    evidence_drafts: list[dict] = Field(default_factory=list)
    discovery_drafts: list[dict] = Field(default_factory=list)
    execution_run_ref: str | None = None
```

Use `dict` for drafts until `Evidence` and `Discovery` schemas are importable without circular dependencies. Add `Field` import from `pydantic`.

## Phase 2: Executor Registry

### Step 4 — Create `ExecutorRegistry`

**File**: `src/agents/executor/registry.py` (new file)

Create an `ExecutorRegistry` class following the `NodeRegistry` pattern in `src/agents/utilities/nodes_registry.py`.

Key design points:
- The decorator instantiates the executor class at registration time (executors are stateless).
- Duplicate capability registration raises `ValueError`.
- `get()` raises `CapabilityNotFoundError` for unknown capabilities.

Create a module-level singleton `executor_registry = ExecutorRegistry()` for convenience.

### Step 5 — Register existing executors

**Files**:
- `src/agents/executor/graph_miner/agent.py`
- `src/agents/executor/hypothesis_analyst/agent.py`

Annotate the executor classes:

```python
from ..registry import executor_registry
from ..types import Capability

@executor_registry.register(Capability.GRAPH_MINING)
class GraphMiner(Executor):
    ...
```

## Phase 3: Executor Dispatcher

### Step 6 — Create `ExecutorDispatcher`

**File**: `src/agents/executor/dispatcher.py` (new file)

Thin implementation:

```python
class ExecutorDispatcher:
    def __init__(self, registry: ExecutorRegistry):
        self._registry = registry

    async def dispatch(self, request: ExecutionRequest) -> ExecutionResult:
        executor = self._registry.get(request.capability)
        return await executor.run(request.input, request.context)
```

## Phase 4: Planner Node Implementation

Depends on Phase 1–3 completion.

### Step 7 — Implement `prepare_execution`

**File**: `src/agents/planner/nodes.py`

Map `TaskKind` to `Capability` and place an `ExecutionRequest` in planner state (`state.pending_execution_request`). Use a simple module-level mapping `TASK_KIND_TO_CAPABILITY`.

### Step 8 — Implement `dispatch_executor`

**File**: `src/agents/planner/nodes.py`

Call `await runtime.context.dispatcher.dispatch(request)` and store `state.last_execution_result`.

Update planner `Context` (`src/agents/planner/types.py`) to include `dispatcher: ExecutorDispatcher` and `State` to include `pending_execution_request` and `last_execution_result`.

## Phase 5: Tests

### Step 9 — Test `ExecutorRegistry`

Create `tests/agents/test_executor_registry.py` to verify registration, duplicate detection, and lookup behavior.

### Step 10 — Test `ExecutorDispatcher`

Create `tests/agents/test_executor_dispatcher.py` to verify dispatching and error handling.

### Step 11 — Integration test

Create `tests/agents/test_executor_dispatch_integration.py` to verify end-to-end routing to `GraphMiner` and `HypothesisAnalyst`.

## File Change Summary

| File | Action |
|---|---|
| `src/agents/executor/types.py` | Add `Capability` enum, update `ExecutionRequest`, update `ExecutionResult` |
| `src/agents/executor/registry.py` | Create — `ExecutorRegistry` |
| `src/agents/executor/dispatcher.py` | Create — `ExecutorDispatcher` |
| `src/agents/executor/graph_miner/agent.py` | Add `@executor_registry.register(Capability.GRAPH_MINING)` |
| `src/agents/executor/hypothesis_analyst/agent.py` | Add `@executor_registry.register(Capability.HYPOTHESIS_TESTING)` |
| `src/agents/planner/nodes.py` | Implement two nodes and mapping dict |
| `tests/agents/*` | Create registry/dispatcher/integration tests |

## Out of Scope

- Message bus / process isolation
- Multi-executor-per-capability priority selection
- Full `review_execution` persistence logic

---

Follow this README for an incremental implementation. Implement phase-by-phase and run the new tests after each phase.
