# Application Layer Package (`src/application/`)

> **Role:** Package technical reference. **Canonical concept owner:**
> [Persistence and transactions](../../docs/operations/persistence-and-transactions.md).
> **Contributor entry:** [Contributor documentation](../../docs/development/index.md).
> **Current-state owner:** [CogniEDA current state](../../docs/current-state.md).

> Canonical documentation:
> [Runtime composition](../../docs/operations/runtime-composition.md)
> and
> [Persistence and transactions](../../docs/operations/persistence-and-transactions.md).
> Planner and product-process boundaries:
> [Planner operations and approvals](../../docs/operations/planner-and-approvals.md)
> and
> [Product bootstrap](../../docs/operations/product-bootstrap.md).
> Contributor map: [Contributor documentation](../../docs/development/index.md).

## Purpose
The `application` layer coordinates domain transactions, execution transitions, governance decisions, scientific admissions, and validity propagation across CogniEDA bounded contexts.

## Owned Responsibilities
- Fenced execution transition management (`application.execution`).
- Evidence admission (`application.evidence`).
- Protected hypothesis evaluation controls (`application.evaluation`).
- Proposal decision recording & governance (`application.governance`).
- Atomic discovery materialization (`application.discovery`).
- Atomic validity propagation (`application.validity`).
- Planner operation commit orchestration (`application.orchestrator`).
- In-process composition root (`application.runtime`) and external factory loader
  (`application.runtime_loader`).

## Forbidden Responsibilities
- Direct SQLModel table manipulation outside owned transaction boundaries.
- Modifying scientific claim text inside application code.
- Exposing generic lifecycle mutators on repositories.

## Subpackages
- [bootstrap](bootstrap/README.md)
- [discovery](discovery/README.md)
- [evaluation](evaluation/README.md)
- [events](events/README.md)
- [evidence](evidence/README.md)
- [execution](execution/README.md)
- [governance](governance/README.md)
- [orchestrator](orchestrator/README.md)
- [validity](validity/README.md)

`bootstrap/` and `events/` are documentation-only target packages. They contain
no Python implementation and are not the current composition root.
