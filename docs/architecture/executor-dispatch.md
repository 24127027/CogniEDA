# Data Explorer Dispatch

> **Current implementation snapshot:** 2026-07-25 working tree. This page distinguishes durable
> attempt ownership from Data Explorer invocation.
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
  -> DataExplorerRegistry resolves the exact configured Data Explorer executor id
  -> adapter.run(DataExplorerInput, DataExplorerExecutionContext)
  -> canonical DataExplorerResult
  -> receiver validates and stores one fenced inbox envelope
  -> Evidence-admission coordinator atomically commits AnalysisFrame/Evidence
```

`PreparedExecution` is the serialized analytical payload, but it is not the sole attempt-identity authority. The matching `ExecutionRunRecord` and `ExecutionOutboxRecord` own the run id, dispatch key, lease epoch, executor id, method id and parameter hash. The durable worker combines these records, validates their agreement and binds canonical FCO UUIDs before the capability adapter runs.

## Contract ownership

| Contract/component | Owner | Role |
| --- | --- | --- |
| `PreparedExecution` plus run/outbox records | `application.execution` / `schemas.execution` | Durable transport and immutable attempt identity |
| `DataExplorerInput` | `agents.executor` | Non-persisted scientific request with Task, Hypothesis, DataProfile and ExecutionRun UUIDs |
| `DataExplorerExecutionContext` | Worker process | Non-persisted operational dependency seam; currently empty |
| `DataExplorerAdapterProtocol` | `agents.executor` | Narrow role-specific invocation surface returning `DataExplorerResult` |
| `DataExplorerRegistry` | `agents.executor` | One explicit executor id/factory per runtime; exact lookup, lazy construction and adapter validation only |
| `DataExplorerAdapter` | `agents.executor` | Data Explorer-specific LangGraph validation adapter |
| `DataExplorerDispatcher` | `agents.executor` | Translate a validated prepared contract, invoke one Data Explorer adapter, and validate its actual return value as `DataExplorerResult` |
| `DataExplorerResult` | `schemas.execution.data_explorer` | Canonical observation-only executor and durable receipt type |
| execution method/result hashing | `application.execution.identity` | Pure canonical identity helpers for durable execution contracts and receipts |
| `finalize_attempt()` | `application.execution.recovery` | Restart-safe, fenced Evidence admission recovery coordinator |

`DataExplorerInput` contains the application-bound `execution_run_id`, `task_id`, `hypothesis_id`, and
`data_profile_id`, plus the dataset path, admitted hypothesis and execution specification, and
deterministic seed.

It does not contain Planner state, SessionFrame, raw chat, Assumptions, Task motivation, retrieval scores, SQL sessions, repositories or transition services.

## Registry and availability

The supported composition root requires an explicit Data Explorer executor id and factory, creates
one private registry, and permits exactly that one registration. Current admitted analytical Tasks
use `executor_id="deterministic"`, so a runtime executing current planner work must configure the
same id. Unknown ids fail exact lookup; there is no fallback. Registration is an ordinary method,
not a decorator, and imports cannot mutate registry state.

Graph Miner and Hypothesis Analyst are not exported as executor aliases and have no registry
registration. Factory construction is lazy. Missing registration, construction errors, malformed
adapters and invocation errors become controlled technical-failure receipts in the durable worker
without fake Evidence.

## Retry and result semantics

Technical retry creates a new `ExecutionRun` and outbox, reuses the same Hypothesis and persisted analytical payload, and re-enters the same worker/adapter path. The worker binds the successor run id while preserving Task, Hypothesis, DataProfile, method and parameter identity. Lease and receiver fencing prevent a stale predecessor delivery from finalizing the successor.

Executors cannot return or redefine the receiver's run id, dispatch key, lease epoch, Task,
Hypothesis, DataProfile, approved executor, or parameter hash. Evidence observations repeat the
executed method and parameters because those are scientific provenance; application processing
rejects any mismatch with the approved durable contract. Duplicate result digests remain
idempotent and conflicting duplicates remain quarantined by the transition service.

## Compatibility status

Generic `ExecutorRegistry`, `ExecutorDispatcher`, `ExecutorInput`, and `ExecutorContext` names were
normalized to role-specific `DataExplorer*` symbols. Compatibility aliases including
`DataExplorerExecutor`, `GraphMinerExecutor`, and `HypothesisAnalystExecutor`, generic executor
state, decorator registration, cross-specialist capability-selection helpers, `ExecutionRequest`,
`ExecutorOutput`, and legacy `ExecutorResult` were removed. No compatibility branch bypasses
`DataExplorerDispatcher`.

The mixed `ExecutorResult`, compatibility bridge, and application-authored evaluator are deleted.
Legacy inbox parsing exists only in `db.legacy_migration`, which quarantines rather than promotes
unverified scientific content.

## Not yet implemented

- concrete Data Explorer and Graph Miner implementations;
- production authentication/model/Data Explorer adapters, service API, and worker process;
- concrete operational fields or cooperative-cancellation callback in `DataExplorerExecutionContext`;
- executor delegation, authorization, tracing or cycle/depth policy;
- deployment infrastructure beyond the fail-closed composition contract.

`CogniEDARuntime.propagate_validity()` delegates to
`AtomicValidityPropagationService.execute_propagation()` under the configured session boundary; it
does not duplicate transaction logic. That facade, Evidence/Discovery admission, and migration
support are currently SQLite-only. No CLI, service loop, or worker bootstrap is supported.
Package S1-B execution/Evidence restructuring and S2-A protected-evaluation/governance
restructuring are implemented. Atomic Discovery admission and validity propagation remain under
`application.orchestrator`; their S2-B/S3 decomposition is deferred.

These gaps mean CogniEDA is not an end-to-end analytical product even though the local
durable-to-domain contract is normalized.

See [Implementation Gap Analysis](implementation-gap-analysis.md).
