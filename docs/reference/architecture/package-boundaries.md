# Package boundaries

> **Role:** Technical reference. **Canonical concept owner:**
> [Runtime composition](../../operations/runtime-composition.md).
> **Contributor entry:** [Contributor documentation](../../development/index.md).
> **Current-state owner:** [CogniEDA current state](../../current-state.md).

> **Implementation status:** package ownership **Implemented**; runtime
> deployment surfaces **Partially implemented**; persistence guarantees
> **Verified on SQLite**.

The canonical authority explanation is
[Scientific authority](../../concepts/scientific-lifecycle/scientific-authority.md). Runtime and persistence
ownership are explained by
[Runtime composition](../../operations/runtime-composition.md) and
[Persistence and transactions](../../operations/persistence-and-transactions.md).
Planner coordination is owned by
[Planner operations and approvals](../../operations/planner-and-approvals.md);
product-process absence is owned by
[Product bootstrap](../../operations/product-bootstrap.md).
This page retains the package and dependency map for contributors.

## Current package map

| Context | Schemas | Repositories | Tables | Application owner / entry |
| --- | --- | --- | --- | --- |
| research | `schemas.research` | `repositories.research` | objectives, revisions, profiles, assumptions, tasks, hypotheses, session frames | `application.orchestrator.planner_commit`; Planner nodes |
| workflow | `schemas.planner_operations` | `repositories.planner_operation_repository` | planner operations | Planner proposal/decision nodes and `commit_planner_operations` |
| execution | `schemas.execution` | `repositories.execution` | runs, approvals, outbox, inbox | `application.execution` |
| evidence | `schemas.evidence` | `repositories.evidence` | analysis frames, evidence | `application.evidence` plus execution finalizer |
| evaluation | `schemas.evaluation` | `repositories.evaluation` | evaluation controls | `application.evaluation` |
| governance | `schemas.governance` | `repositories.governance` | user decisions, authorities, proposal decisions | `application.governance` |
| discovery | `schemas.discovery` | `repositories.discovery` | discoveries, admission claims | `application.discovery` |
| validity | `schemas.validity` | `repositories.validity` | validity events | `application.validity` |
| runtime | typed configuration in `application.runtime` | none | none | `CogniEDARuntime`, `runtime_loader` |
| retrieval | `schemas.retrieval` and context summaries | research/discovery repositories | no index table | `memory.retrieval_engine`, `retrieval_policy`, `session_frame` |

`db.models` is the explicit persistence compatibility facade. Its bounded
implementation modules own physical mappings, not domain schemas or
repositories.

## Dependency rules

- schemas import no application or repository modules;
- repositories may import schemas and `db.models`, but no application services;
- application services coordinate repositories and own commits;
- specialist packages import no persistence/application mutation services;
- adjacent application packages use explicit coordination rather than re-export aliases;
- direct imports of table classes use the `db.models` facade outside the model implementation.

## Scaffold-only directories

`src/application/bootstrap/` and `src/application/events/` contain READMEs only. They are not active
Python bounded contexts. Graph Miner has stub code but no runtime registration.

See [Source ownership](source-ownership.md) for write ownership and dependencies.
