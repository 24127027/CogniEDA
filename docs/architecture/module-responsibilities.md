# Module responsibility matrix

> **Role:** Technical reference. **Canonical concept owner:**
> [Persistence and transactions](../operations/persistence-and-transactions.md).
> **Contributor entry:** [Contributor documentation](../development/index.md).
> **Current-state owner:** [CogniEDA current state](../current-state.md).

> **Implementation status:** **Implemented** for the checked-in modules; missing
> deployment adapters are **Deferred**.

The operational rationale is owned by
[Runtime composition](../operations/runtime-composition.md) and
[Persistence and transactions](../operations/persistence-and-transactions.md).
Planner coordination is owned by
[Planner operations and approvals](../operations/planner-and-approvals.md);
retrieval ranking and scale are owned by
[Retrieval strategy](../concepts/context/retrieval-strategy.md).
This page remains a contributor-facing package map.

| Module | Owns | Must not own | Runtime entry |
| --- | --- | --- | --- |
| `agents.planner` | request routing, proposal construction, durable approval/staging orchestration | Evidence/Discovery creation or scientific evaluation | `Planner.run`, `CogniEDARuntime.planner` |
| `agents.executor` | one explicit observation-only Data Explorer registry/dispatch boundary | durable state or cross-specialist registry | `application.execution.dispatch` |
| `agents.executor.hypothesis_analyst` | protected evaluation and proposal/failure output | tools, persistence, decisions, raw data | `application.evaluation.runner` |
| `application.orchestrator.planner_commit` | atomic approved PlannerOperation batches; research/workflow mutations; execution admission delegation | Evidence/Discovery materialization or terminal scientific bypass | Planner `commit` and execution-contract node |
| `application.execution` | attempt admission, leases, outbox/inbox, receipt, cancellation, retry, reconciliation | Evidence/Discovery wording or creation | runtime dispatch/reconcile and finalizer |
| `application.evidence` | validated deterministic admission plan and atomic AnalysisFrame/Evidence chain | hypothesis evaluation or Discovery | execution finalizer |
| `application.evaluation` | protected bundle construction and fenced evaluation-control lifecycle | governance decisions or Discovery admission | runtime evaluation |
| `application.governance` | authenticated authority issuance and exact proposal decision recording | proposal wording or Discovery creation | runtime authority/decision methods |
| `application.discovery` | plan identity, claims, replay/fencing, exact Discovery/conclusion-frame transaction | Analyst invocation or decision creation | runtime admission coordinator |
| `application.validity` | command/plan verification, dependency traversal, atomic validity event/transition transaction | claim authoring | runtime validity facade |
| `memory` | SessionFrame projection policy and bounded Discovery retrieval | protected evaluation authority or persistent vector index | Planner decomposition helpers |
| `data` | loaders, validation, baseline profiling, DVC protocol | governed product import/cleaning workflow | direct library calls only |

## Persistence layer distinctions

- Domain schemas are typed values under `schemas`.
- Repositories convert/query/stage values.
- SQLModel table classes live under `db.models`.
- Migrations and SQLite triggers repair or guard physical schema.

None of those layers is interchangeable, and repository existence does not grant transaction
authority.
