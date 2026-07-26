# Structural foundation status

> **Role:** Technical reference. **Canonical concept owner:**
> [CogniEDA current state](../current-state.md).
> **Contributor entry:** [Contributor documentation](../development/index.md).
> **Current-state owner:** [CogniEDA current state](../current-state.md).

> **Technical-scope qualification:** this reference maps the current in-process
> structural boundaries. Guarded persistence behavior is **Verified on SQLite**;
> project-wide maturity and product support remain owned by the current-state
> pages linked below.

This page retains the current implementation structural boundary that
contributors need.
Checkout-specific baselines, command output, object counts, and implementation
history belong in ignored local audit records rather than canonical
documentation.

The canonical maturity narrative is
[CogniEDA current state](../current-state.md). Capability comparison belongs to
the [capability and maturity map](../capability-and-maturity-map.md), and future
dependencies belong to the [roadmap](../roadmap.md).

Canonical operational ownership is explained in
[Runtime composition](../operations/runtime-composition.md),
[Product bootstrap](../operations/product-bootstrap.md),
[Planner operations and approvals](../operations/planner-and-approvals.md),
[Retrieval strategy](../concepts/context/retrieval-strategy.md),
[SessionFrame scaling and resume limits](../concepts/context/session-frame-scaling.md),
[Persistence and transactions](../operations/persistence-and-transactions.md),
and [SQLite and portability](../operations/sqlite-and-portability.md).

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
