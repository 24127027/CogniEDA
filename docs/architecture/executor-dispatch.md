# Executor Dispatch

> **Current implementation snapshot:** 2026-07-16. This page distinguishes the agent capability adapter from the durable application worker.

## Current implementation: capability adapter

`src/agents/executor/` implements:

| Component | Role |
| --- | --- |
| `CapabilitySpec` and canonical capability ids | Catalog and descriptions for `data_exploration`, `graph_mining`, and `hypothesis_testing`. |
| `ExecutionRequest` | Typed capability/input/context request; validates against the catalog. |
| `ExecutorRegistry` | Registers specs/factories, guards duplicates and lazily creates singleton executor wrappers. |
| `ExecutorDispatcher` | Resolves one registered capability and calls `executor.run(...)`. |
| Capability selection helpers | Build a constrained Pydantic selection model and instructions for an allowed subset. |

Registration status:

| Capability | Registered | Runnable default graph |
| --- | --- | --- |
| `data_exploration` | No | No |
| `graph_mining` | `GraphMinerExecutor` | No; graph builder raises `NotImplementedError` |
| `hypothesis_testing` | `HypothesisAnalystExecutor` | No; graph builder raises `NotImplementedError` |

The catalog boundary and registry boundary are different: an `ExecutionRequest` can accept a catalogued id for which registry resolution later raises `KeyError`.

## Current implementation: durable application worker

`src/application/orchestrator/dispatcher.py` is not the same dispatcher. It consumes persisted execution attempts:

```text
ExecutionOutbox(pending)
  -> claim_dispatch(worker/lease/epoch/version)
  -> injected executor.execute(prepared_payload)
  -> receive_executor_result
  -> ExecutionInbox
```

The injected object only needs the application worker's `execute(prepared)` contract. Current source has no adapter that resolves `executor_type` through `agents.executor.ExecutorRegistry`.

## Planner boundary

The compiled planner graph prepares and approves an execution contract, then commits `Hypothesis`, `ExecutionRun`, and outbox state. It ends after admission. Dispatch, result receipt and scientific finalization are independent worker operations outside the graph.

This avoids treating executor output as durable knowledge. The finalizer validates the persisted result and produces operations for `AnalysisFrame`, `Evidence`, `Discovery`, lifecycle changes and `SessionFrame` before the fenced transaction commits.

## Not yet implemented

- runnable default GraphMiner/HypothesisAnalyst graphs;
- a registered data-exploration executor;
- planner capability selection integrated with prepared execution;
- durable-worker-to-capability-registry adapter;
- concrete Evidence/Discovery draft fields on `ExecutionResult`;
- caller authorization, delegation tracing, retry and cycle/depth protection in the capability layer;
- production worker bootstrap.

## Target design constraint

Future integration must keep write ownership in the durable attempt/finalization boundary. An executor or capability dispatcher must not directly persist Evidence or Discovery, mutate attempt state, or bypass user approval.

See [Implementation Gap Analysis](implementation-gap-analysis.md).
