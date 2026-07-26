# Product bootstrap

CogniEDA has an in-process application runtime. It does not yet have a supported
product process.

> **Implementation status:** `CogniEDARuntime`, explicit dependency injection,
> SQLite initialization, and the external runtime-factory loader seam are
> **Implemented**. A production CLI, HTTP API, worker, daemon, product
> bootstrap, production identity adapter, concrete Data Explorer, and complete
> restart-safe coordination are **Unsupported**. The seam toward a coherent
> product slice is **Partially implemented**.

[Runtime composition](runtime-composition.md) remains
the owner of runtime construction and injected dependencies. This page owns the
difference between that library boundary and an operable product surface.

## Runtime is not product bootstrap

`CogniEDARuntime` is a library composition root. Given an explicit database URL,
principal resolver, Analyst model, Data Explorer identity and factory, and
Planner context factory, it initializes the database and composes the Planner,
executor registry, dispatch, reconciliation, and scientific application
facades.

That makes the authority graph visible and testable in one process. It does not
provide:

- command parsing or a supported console entry point;
- HTTP routing, authentication middleware, or an API lifecycle;
- a long-running execution worker or daemon;
- workspace, Objective, session, or user selection;
- a user approval and resume interface;
- provider credential acquisition or production adapter selection;
- restart orchestration, supervision, or health policy; or
- deployment packaging, observability, and operational recovery.

Direct test construction and ad hoc Python calls exercise a library. They are
not a supported product contract.

## Current product-surface inventory

| Surface | Current status | Boundary |
| --- | --- | --- |
| in-process `CogniEDARuntime` | **Implemented** | library composition and application facades |
| `COGNIEDA_RUNTIME_FACTORY` loader | **Implemented** | imports and type-checks a deployment-supplied factory |
| database initialization | **Verified on SQLite** | local schema, upgrades, triggers, and quarantine |
| direct Planner and application facade calls | **Implemented** | library invocation, not a product process |
| packaged CLI | **Unsupported** | no project script or console bootstrap |
| HTTP API | **Unsupported** | no supported router or service lifecycle |
| worker or daemon | **Unsupported** | no production run loop, supervision, or recovery coordinator |
| Python product bootstrap package | **Unsupported** | `src/application/bootstrap/` contains orientation only |
| production identity | **Unsupported** | principal resolution must be injected |
| production Analyst provider | **Unsupported** | the runtime requires a configured model |
| concrete production Data Explorer | **Unsupported** | an identity and factory must be injected |
| Graph Miner | **Unsupported** | no executable registered production capability |
| tracked default agent capability configuration | **Known deviation** | configured MCP names are undefined and configured skill directories contain no tracked definitions |

An internal `__main__` helper in the Planner graph module renders graph
structure for development. It is not a product entry point. A dependency such
as Typer in `pyproject.toml` likewise does not establish a CLI.

## The runtime-factory seam

`runtime_loader` reads `COGNIEDA_RUNTIME_FACTORY=module:factory`, imports the
callable, invokes it, and requires a `CogniEDARuntime` result. This is a
deployment-supplied seam: it allows an environment to choose credentials,
models, adapters, and workspace configuration without hard-coding them in the
library.

The seam is useful but intentionally narrow. It does not:

- define a supported deployment contract beyond returning the runtime;
- provide production authentication or authorization;
- choose a concrete Analyst or Data Explorer;
- run a request, worker, or reconciliation loop;
- expose approvals to a user; or
- restore an interrupted product session.

It is a **Partially implemented** product seam, not product bootstrap.

## Tracked capability configuration is not a deployment

`config/agents.toml` assigns `filesystem` to the Planner and Hypothesis Analyst
and `neo4j` to Graph Miner, while `config/mcp.toml` contains only commented
examples. `ToolManager` therefore fails explicitly when a configured
PydanticAI adapter asks for one of those undefined MCP toolsets. In addition,
`config/skills.toml` names skill directories under `skills/`, but the tracked
tree contains no `SKILL.md` definitions there.

This is a **Known deviation** in the checked-in developer configuration and a
product-readiness blocker, not a scientific-authority bypass. Explicit slash
commands and tests with injected fakes can still exercise bounded Planner
paths. A deployment must provide a coherent, validated agent/MCP/skill
configuration before model-backed Planner adapters are a supported capability.

## Minimum coherent product boundary

A first supported product surface needs one complete slice rather than a thin
wrapper around the runtime. At minimum it must define:

1. deployment configuration and secret loading;
2. a production principal and authorization policy;
3. workspace, Objective, Planner session, and SessionFrame selection;
4. SQLite database lifecycle and migration failure handling;
5. coherent, validated model, MCP, tool, and skill configuration;
6. a configured production Analyst provider;
7. a concrete Data Explorer and executable method registry;
8. typed request, approval, cancellation, clarification, and resume
   interactions;
9. execution dispatch, receipt, reconciliation, and restart recovery;
10. user-visible results, controlled failures, and stale-state reporting;
11. logs, health, resource limits, and operational ownership; and
12. security, compatibility, and release policy for the chosen interface.

The interface can initially be a CLI, API, desktop process, or another bounded
host. Its shape is secondary to preserving the same authority, transaction,
validity, replay, and recovery semantics as the library.

## Why the product surface is deferred

Shipping a demonstration wrapper now would provide earlier manual integration
feedback and a visible entry point. It would also invite users to depend on
missing identity, adapter, approval, restart, and recovery semantics.

Deferral has concrete costs:

- no immediate supported CLI or product demo;
- delayed end-to-end operational feedback;
- slower validation of user interaction and packaging choices; and
- continued reliance on tests and library composition for integration evidence.

The benefit is that an interface cannot accidentally become a second authority
path, silently lose approvals on restart, or imply a worker and recovery model
that the project has not implemented.

This is not a ban on prototypes. It is a ban on describing a wrapper as a
supported product before its authority and recovery boundary is coherent.

## Implications for the next product-integration slice

The next product-integration work must not begin by adding command syntax. Its
blocking prerequisites are:

- production identity and authorization;
- coherent deployment capability configuration;
- a configured Analyst provider;
- a concrete Data Explorer;
- durable user-interaction coordination across restart; and
- one end-to-end slice that proves request, approval, execution,
  reconciliation, scientific finalization, and user-visible outcome.

Planner persistence coupling does not currently block that preparatory work:
no alternate scientific writer was found, and durable proposals and approvals
already exist. It becomes a product risk when service separation, multiple
sessions or users, repeated approval types, or restart coordination make direct
Planner repository composition hard to govern. That is the extraction trigger
for the application facade described in
[Planner operations and approvals](planner-and-approvals.md).

The current documentation boundary is therefore non-blocking, while the absent
adapters and bootstrap coordination remain product blockers.

## Revisit triggers

Revisit the no-supported-surface decision when:

- a concrete production Data Explorer exists;
- production identity and authorization exist;
- an Analyst provider is configured through deployment policy;
- restart-safe approval, execution, and reconciliation coordination exists;
- one end-to-end product slice passes through the canonical transaction owners;
  and
- an interface has explicit operational ownership and failure semantics.

Any product surface must preserve typed research state, Assumption quarantine,
protected evaluation, exact proposal-copy, canonical scientific writers,
atomic complete effects, SQLite qualification, deterministic replay and
conflict, historical retention, active invalidation, and user-visible context
governance.

## Related canonical concepts

- [Runtime composition](runtime-composition.md)
- [Planner operations and approvals](planner-and-approvals.md)
- [SessionFrame scaling and resume limits](../concepts/context/session-frame-scaling.md)
- [Persistence and transactions](persistence-and-transactions.md)
- [A product interface requires complete bootstrap](../design-decisions/product-interface-requires-complete-bootstrap.md)

## Implementation orientation

The composition root is in `src/application/runtime.py`; the external factory
loader is in `src/application/runtime_loader.py`; and the bootstrap package
status is recorded in `src/application/bootstrap/README.md`. Planner graph
construction is in `src/agents/planner/graph.py`. Runtime and composition tests
are under `tests/application/`, with unsupported-surface enforcement under
`tests/architecture/`.
