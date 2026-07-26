# Structural foundation status

> **Implementation status:** **Partially implemented** overall.
>
> The guarded scientific path described below is **Implemented** and
> **Verified on SQLite**. A supported end-user product surface is
> **Unsupported**.

This page retains the durable structural boundary that contributors need.
Checkout-specific baselines, command output, object counts, and implementation
history belong in ignored local audit records rather than canonical
documentation.

Canonical operational ownership is explained in
[Runtime and composition boundary](../runtime-and-composition-boundary.md),
[Product surface and bootstrap boundary](../product-surface-and-bootstrap-boundary.md),
[Planner boundary and operation model](../planner-boundary-and-operation-model.md),
[Retrieval strategy and scaling](../retrieval-strategy-and-scaling.md),
[SessionFrame scaling and resume boundary](../session-frame-scaling-and-resume-boundary.md),
[Persistence and transaction ownership](../persistence-and-transaction-ownership.md),
and [SQLite boundary and portability](../sqlite-boundary-and-portability.md).

## Current authority map

| Context | Canonical source owner | Transaction or mutation owner | Durable limitation |
| --- | --- | --- | --- |
| research and workflow | research schemas, models, repositories, and Planner operations | `commit_planner_operations` plus scoped application services | Planner nodes still know sessions and repository records |
| execution | `src/application/execution/` | execution transition and coordination services | no production worker process; external effects are at-least-once |
| Evidence | `src/application/evidence/` | atomic Evidence admission | no concrete production Data Explorer |
| evaluation | `src/application/evaluation/` | protected evaluation transition service | deployment must provide a model adapter |
| governance | `src/application/governance/` | authority issuer and decision service | deployment must provide authenticated principal resolution |
| Discovery | `src/application/discovery/` | atomic Discovery admission service | SQLite locking and trigger behavior are the verified boundary |
| validity | `src/application/validity/` | atomic validity propagation service | production authorization workflow is absent |
| retrieval and SessionFrame | `src/memory/` plus research/Discovery repositories | append paths and validity services | no Graph Miner, persistent semantic index, or complete resume UX |

## Preserved scientific authority

The implemented in-process path separates authority as follows:

- the Data Explorer contract is observation-only;
- protected Hypothesis evaluation alone authors typed proposal wording from a
  closed repository-built bundle;
- governance records principal-bound authority and a decision over that exact
  proposal;
- atomic Discovery admission alone materializes the authorized proposal and
  terminal scientific chain;
- atomic validity propagation alone records a validity event and applies its
  dependency plan;
- repositories provide bounded persistence operations but do not own these
  multi-record scientific transactions.

The Planner may stage and commit governed workflow operations, but supported
generic paths fail closed for direct AnalysisFrame, Evidence, Discovery, inbox,
and unsupported execution-run mutation. Its direct knowledge of sessions and
repositories is a **Known deviation**, not a scientific-writer bypass.

## Explicit limitations

- **Unsupported:** production CLI, API, worker, and daemon entry points.
- **Unsupported:** production authentication, model, and Data Explorer
  adapters.
- **Partially implemented:** Planner answer, suggestion, pause, conflict,
  assumption, and resume paths.
- **Known deviation:** the Planner still authors the analytical contract and
  reaches some persistence concerns directly; fresh admission remains guarded,
  while approved-failure recovery and existing-Hypothesis reuse are incomplete.
- **Partially implemented:** SessionFrame governance and project resume.
- **Deferred:** Graph Miner traversal, persistent semantic indexing, executable
  DVC/cleaning, and Evidence cache.
- **Known deviation:** strict static typing remains repository debt.
- **Known deviation:** targeted in-code migration history has no immutable
  revision registry, and supported-path ORM boundaries are not absolute against
  direct database access.
- **Verified on SQLite:** scientific admission and validity transactions; no
  broader database guarantee is made.

These limitations constrain product scope. They do not change the authority
rules of the supported in-process scientific path.
