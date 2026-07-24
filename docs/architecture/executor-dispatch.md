# Data Explorer Dispatch

> **Current implementation snapshot:** 2026-07-24 working tree. This page distinguishes durable
> attempt ownership from capability invocation.
> **Classification:** implementation note rather than target ownership specification. The
> [Agent Responsibility Boundaries](agent-responsibility-boundaries.md) supersede the generic
> executor contract where roles differ.

## Current implementation

The implemented local path is:

```text
ExecutionOutbox(pending)
  -> application worker claims run/outbox lease
  -> worker validates PreparedExecution against immutable run/outbox identity
  -> worker replaces transient local handles with durable Task/Hypothesis/DataProfile UUIDs
  -> agents.executor.DataExplorerDispatcher builds DataExplorerInput
  -> DataExplorerRegistry lazily resolves one Data Explorer factory
  -> adapter.run(DataExplorerInput, DataExplorerExecutionContext)
  -> canonical DataExplorerResult
  -> receiver validates and stores one fenced inbox envelope
  -> Evidence-admission coordinator atomically commits AnalysisFrame/Evidence
```

`PreparedExecution` is the serialized analytical payload, but it is not the sole attempt-identity authority. The matching `ExecutionRunRecord` and `ExecutionOutboxRecord` own the run id, dispatch key, lease epoch, executor id, method id and parameter hash. The durable worker combines these records, validates their agreement and binds canonical FCO UUIDs before the capability adapter runs.

## Contract ownership

| Contract/component | Owner | Role |
| --- | --- | --- |
| `PreparedExecution` plus run/outbox records | `application.orchestrator` | Durable transport and immutable attempt identity |
| `DataExplorerInput` | `agents.executor` | Non-persisted scientific request with Task, Hypothesis, DataProfile and ExecutionRun UUIDs |
| `DataExplorerExecutionContext` | Worker process | Non-persisted operational dependency seam; currently empty |
| `DataExplorerRegistry` | `agents.executor` | Duplicate-safe Data Explorer registration and lazy factory resolution only |
| `DataExplorerAdapter` | `agents.executor` | Data Explorer-specific LangGraph validation adapter |
| `DataExplorerDispatcher` | `agents.executor` | Translate a validated prepared contract, invoke one Data Explorer adapter, and validate its actual return value as `DataExplorerResult` |
| `DataExplorerResult` | `schemas.data_explorer_contracts` | Canonical observation-only executor and durable receipt type |
| `finalize_attempt()` | `application.orchestrator.finalizer` | Historical function name for restart-safe, fenced Evidence admission only |

`DataExplorerInput` contains the application-bound `execution_run_id`, `task_id`, `hypothesis_id`, and
`data_profile_id`, plus the dataset path, admitted hypothesis and execution specification, and
deterministic seed.

It does not contain Planner state, SessionFrame, raw chat, Assumptions, Task motivation, retrieval scores, SQL sessions, repositories or transition services.

## Registry and availability

The supported composition root explicitly registers only the supplied `data_exploration` factory.
Graph Miner and Hypothesis Analyst are not registered in this dispatcher. Factory construction is
lazy and factory failures cross the adapter as controlled failed receipts without fake Evidence.

## Retry and result semantics

Technical retry creates a new `ExecutionRun` and outbox, reuses the same Hypothesis and persisted analytical payload, and re-enters the same worker/adapter path. The worker binds the successor run id while preserving Task, Hypothesis, DataProfile, method and parameter identity. Lease and receiver fencing prevent a stale predecessor delivery from finalizing the successor.

Executors cannot return or redefine the receiver's run id, dispatch key, lease epoch, Task,
Hypothesis, DataProfile, approved executor, or parameter hash. Evidence observations repeat the
executed method and parameters because those are scientific provenance; application processing
rejects any mismatch with the approved durable contract. Duplicate result digests remain
idempotent and conflicting duplicates remain quarantined by the transition service.

## Compatibility status

Generic `ExecutorRegistry`, `ExecutorDispatcher`, `ExecutorInput`, and `ExecutorContext` names were normalized to role-specific `DataExplorer*` symbols. `ExecutionRequest`, `ExecutorOutput`, and legacy `ExecutorResult` types were removed. No compatibility branch bypasses `DataExplorerDispatcher`.

The mixed `ExecutorResult`, compatibility bridge, and application-authored evaluator are deleted.
Legacy inbox parsing exists only in `db.legacy_migration`, which quarantines rather than promotes
unverified scientific content.

## Not yet implemented

- concrete Data Explorer and Graph Miner implementations;
- production authentication/model/Data Explorer adapters, service API, and worker process;
- concrete operational fields or cooperative-cancellation callback in `DataExplorerExecutionContext`;
- executor delegation, authorization, tracing or cycle/depth policy;
- deployment infrastructure beyond the fail-closed composition contract.

These gaps mean CogniEDA is not an end-to-end analytical product even though the local durable-to-domain contract is normalized.

See [Implementation Gap Analysis](implementation-gap-analysis.md).
