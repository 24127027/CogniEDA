# Executor Dispatch Architecture

## Target Design

The executor dispatch layer decouples *what* needs to happen from *who* does it. Callers (the planner or other executors) declare a **capability** they need fulfilled — such as "hypothesis_testing", "graph_mining", or "data_exploration" — and the **ExecutorDispatcher** resolves which registered executor can fulfill that capability.

This design follows three principles:

1. **Capability-based routing** — the caller names the analytical need, not the executor. The dispatcher owns the mapping.
2. **Uniform interface** — every executor call uses the same `ExecutionRequest → ExecutionResult` contract, regardless of whether the caller is the planner or another executor.
3. **Self-registration** — executors declare their capabilities via a `@registry.register(capability)` decorator at class definition time. No central config file enumerates executors.

### Architecture Diagram

```mermaid
flowchart TD
    P[Planner Node: prepare_execution] -->|maps TaskKind → Capability| ER[ExecutionRequest]
    ER --> D[ExecutorDispatcher]
    D -->|capability lookup| REG[ExecutorRegistry]
    REG -->|resolves to| EX[Executor Instance]
    EX -->|async run| ERES[ExecutionResult]
    ERES --> P2[Planner Node: dispatch_executor]
    P2 --> P3[Planner Node: review_execution]

    E1[GraphMiner] -.->|@register GRAPH_MINING| REG
    E2[HypothesisAnalyst] -.->|@register HYPOTHESIS_TESTING| REG
   E3[DataExplorer] -.->|@register DATA_EXPLORATION| REG
```

### Component Responsibilities

| Component | Responsibility | Location |
|---|---|---|
| `Capability` (StrEnum) | Shared vocabulary of analytical needs | `src/agents/executor/types.py` |
| `ExecutionRequest` | Input contract: capability + task + context | `src/agents/executor/types.py` |
| `ExecutionResult` | Output contract: evidence drafts, discovery drafts, DataProfile drafts, execution run ref | `src/agents/executor/types.py` |
| `ExecutorRegistry` | Decorator-based registry mapping capability → executor instance | `src/agents/executor/registry.py` |
| `ExecutorDispatcher` | Resolves capability to executor, invokes `executor.run()`, returns result | `src/agents/executor/dispatcher.py` |
| `Executor` (ABC) | Base class all executors inherit; provides `run(input, context) → ExecutionResult` | `src/agents/executor/executor.py` |

### Capability Set (Initial)

| Capability | Description | Registered Executor |
|---|---|---|
| `graph_mining` | Search and traverse the knowledge graph | `GraphMiner` |
| `hypothesis_testing` | Execute statistical tests, produce Evidence and Discovery drafts | `HypothesisAnalyst` |
| `data_exploration` | Profile, visualize, and summarize datasets | `DataExplorer` |

Capabilities use a `StrEnum` for type safety while remaining extensible without schema migration — the same pattern used by `FirstClassObjectType` and `TaskKind` in `src/schemas/enums.py`.

### Dispatch Flow

1. **Caller** (planner node or executor node) constructs an `ExecutionRequest` with:
   - `capability`: which analytical need to fulfill
   - `input`: the task and any additional parameters
   - `context`: session frame context for the executor

2. **ExecutorDispatcher.dispatch(request)**:
   - Looks up `request.capability` in the `ExecutorRegistry`
   - If not found → raises `CapabilityNotFoundError`
   - If found → calls `executor.run(request.input, request.context)`
   - Returns the `ExecutionResult`

3. **Caller** receives `ExecutionResult` containing:
   - `evidence_drafts`: list of evidence produced
   - `discovery_drafts`: list of discovery claims produced
   - `execution_run_ref`: provenance reference for the execution

### Planner Integration

Two planner nodes bridge the planner pipeline to the dispatch layer:

- **`prepare_execution`**: Inspects the selected `Task`'s `TaskKind`, maps it to a `Capability`, and constructs an `ExecutionRequest`. The mapping is a simple dictionary.

- **`dispatch_executor`**: Takes the `ExecutionRequest` from planner state, calls `dispatcher.dispatch(request)`, and stores the `ExecutionResult` in planner state for `review_execution` to consume.

### Executor-to-Executor Chaining (Future)

Because the dispatcher exposes a uniform `ExecutionRequest → ExecutionResult` interface, any executor node can call `dispatcher.dispatch()` to invoke another executor. This enables chains like:

```
GraphMiner (find relevant subgraph)
  → dispatcher.dispatch(capability="hypothesis_testing", ...)
    → HypothesisAnalyst (test hypothesis on subgraph)
```

This is architecturally supported but not implemented in the initial version.

### Registration Pattern

Executors self-register using a decorator that mirrors the existing `NodeRegistry` pattern:

```python
# In graph_miner/agent.py
from ..registry import executor_registry
from ..types import Capability

@executor_registry.register(Capability.GRAPH_MINING)
class GraphMiner(Executor):
    ...
```

The `ExecutorRegistry` validates:
- No duplicate capability registrations (one capability → one executor)
- Registered classes are `Executor` subclasses

### Runtime Wiring

The dispatcher is passed to planner nodes via LangGraph's `Runtime[Context]` mechanism. The planner's `Context` model gains a `dispatcher: ExecutorDispatcher` field. This avoids global mutable state and keeps the dispatcher testable — tests inject a dispatcher with mock executors.

## Current Implementation

The dispatch layer exists, but parts of the target design remain scaffold-level. Current state:

- `ExecutionRequest` exists with capability-based routing and validates capability ids at the Pydantic boundary.
- `ExecutionResult` carries draft, evidence reference, log, DataProfile draft, and final-result fields.
- `prepare_execution` and `dispatch_executor` planner nodes are still scaffold-level.
- `GraphMiner` remains scaffold-level, while `HypothesisAnalyst` and `DataExplorer` are registered and have implemented LangGraph workflows.
- `ExecutorRegistry` and `ExecutorDispatcher` exist.
- The planner still has no production mechanism to discover or invoke executors end to end.

## Implementation Status

| Component | Status | Note |
|---|---|---|
| `Capability` enum | Implemented | Capability ids are defined in `src/agents/executor/capabilities.py` |
| `ExecutionRequest` (capability-based) | Implemented | Validates `capability`, `input`, and `context` |
| `ExecutionResult` (structured) | Implemented | Carries evidence, DataProfile, logs, and final-result fields |
| `ExecutorRegistry` | Implemented | Decorator-based registry with lazy singleton resolution |
| `ExecutorDispatcher` | Implemented | Resolves capability ids and invokes executor `run()` |
| `prepare_execution` node | Not implemented | Planner execution bridge remains scaffold-level |
| `dispatch_executor` node | Not implemented | Planner execution bridge remains scaffold-level |
| Executor registration | Implemented | `GraphMiner`, `HypothesisAnalyst`, and `DataExplorer` self-register on import |

## Known Deviations

- No planner-owned dispatcher wiring exists yet, so capability-based executor dispatch is still invoked directly from tests or executor wrappers.
- No `PlannerOperation` schema exists yet, so `prepare_execution` cannot produce a proper operation record — it will directly construct the `ExecutionRequest` in planner state for now.
- `review_execution` cannot persist `Evidence` or `Discovery` because those persistence paths are not yet implemented. The `ExecutionResult` carries drafts that `review_execution` can inspect but not yet commit.

## Related Documents

- [Planner Workflow](planner-workflow.md) — the planner pipeline that calls the dispatcher
- [First-Class Objects](first-class-objects.md) — the `Evidence` and `Discovery` FCOs that executors produce
- [Implementation Gap Analysis](implementation-gap-analysis.md) — tracks the "execution dispatch has no implemented executor integration" gap
