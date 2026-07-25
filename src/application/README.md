# Application Layer Package (`src/application/`)

> Canonical Documentation: [Bounded Contexts](../../docs/architecture/bounded-contexts.md) | [Architecture Overview](../../docs/architecture/overview.md)

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
