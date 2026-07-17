# Executor Dispatch

> **Current implementation snapshot:** 2026-07-17 working tree. This page distinguishes durable attempt ownership from capability invocation.

## Current implementation

The implemented local path is:

```text
ExecutionOutbox(pending)
  -> application worker claims run/outbox lease
  -> worker validates PreparedExecution against immutable run/outbox identity
  -> worker replaces transient local handles with durable Task/Hypothesis/DataProfile UUIDs
  -> agents.executor.ExecutorDispatcher builds ExecutorInput
  -> ExecutorRegistry lazily resolves one executor factory
  -> executor.run(ExecutorInput, ExecutorContext)
  -> canonical ExecutorResult
  -> receiver validates and stores one fenced inbox envelope
  -> finalize_attempt() separately commits scientific state
```

`PreparedExecution` is the serialized analytical payload, but it is not the sole attempt-identity authority. The matching `ExecutionRunRecord` and `ExecutionOutboxRecord` own the run id, dispatch key, lease epoch, executor id, method id and parameter hash. The durable worker combines these records, validates their agreement and binds canonical FCO UUIDs before the capability adapter runs.

## Contract ownership

| Contract/component | Owner | Role |
| --- | --- | --- |
| `PreparedExecution` plus run/outbox records | `application.orchestrator` | Durable transport and immutable attempt identity |
| `ExecutorInput` | `agents.executor` | Non-persisted scientific request with Task, Hypothesis, DataProfile and ExecutionRun UUIDs |
| `ExecutorContext` | Worker process | Non-persisted operational dependency seam; currently empty |
| `ExecutorRegistry` | `agents.executor` | Duplicate-safe registration and lazy factory resolution only |
| `ExecutorDispatcher` | `agents.executor` | Translate a validated prepared contract and invoke one domain executor |
| `ExecutorResult` | `application.orchestrator.execution_contracts` | Sole result schema accepted by the receiver |
| `finalize_attempt()` | `application.orchestrator.finalizer` | Authoritative fenced scientific-result transaction |

The application worker owns leasing, reconstruction, durable identity validation, failure receipt and receiver submission. The capability dispatcher does not mutate attempts or persist scientific objects.

## Domain input and forbidden context

`ExecutorInput` contains only:

- `execution_run_id`, `task_id`, `hypothesis_id`, `data_profile_id`;
- dataset path;
- admitted hypothesis draft and execution specification;
- deterministic seed.

It does not contain Planner state, SessionFrame, raw chat, Assumptions, Task motivation, retrieval scores, SQL sessions, repositories or transition services.

## Registry and availability

`graph_mining` and `hypothesis_testing` have registered wrappers. Their graph builders still raise `NotImplementedError`; registration is not proof of runnable analytical capability. `data_exploration` remains unregistered. Factory construction is lazy and factory failures cross the adapter as controlled dispatch failures in the durable worker.

## Retry and result semantics

Technical retry creates a new `ExecutionRun` and outbox, reuses the same Hypothesis and persisted analytical payload, and re-enters the same worker/adapter path. The worker binds the successor run id while preserving Task, Hypothesis, DataProfile, method and parameter identity. Lease and receiver fencing prevent a stale predecessor delivery from finalizing the successor.

Executors cannot redefine the receiver's run id, dispatch key, lease epoch or admitted method. The canonical result carries bounded observations; scientific processing additionally compares executor, method and parameter identity before producing operations. Duplicate result digests remain idempotent and conflicting duplicates remain quarantined by the transition service.

## Compatibility status

The former scaffold-only `ExecutionRequest`, `ExecutorOutput` and duplicate `ExecutionResult` types had no production call sites. They were removed rather than retained as a second authority. Repository documentation and package exports now describe only the durable adapter path. No compatibility branch bypasses `ExecutorDispatcher`.

## Not yet implemented

- runnable default GraphMiner or HypothesisAnalyst graphs;
- a registered data-exploration executor;
- production CLI, service or worker bootstrap;
- concrete operational fields or cooperative-cancellation callback in `ExecutorContext`;
- executor delegation, authorization, tracing or cycle/depth policy;
- generic scientific method processing beyond the narrow deterministic path.

These gaps mean CogniEDA is not an end-to-end analytical product even though the local durable-to-domain contract is normalized.

See [Implementation Gap Analysis](implementation-gap-analysis.md).
