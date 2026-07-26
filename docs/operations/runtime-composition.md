# Runtime composition

CogniEDA needs one visible place where persistence, transaction services,
specialists, identity resolution, and deployment adapters are assembled. The
current answer is an explicit in-process runtime. It is a composition boundary,
not a product interface or a deployment topology.

> **Implementation status:** `CogniEDARuntime` and the external runtime-factory
> loader are **Implemented**. Persistence initialization through that runtime is
> **Verified on SQLite**. A packaged CLI, HTTP service, worker, daemon,
> production identity provider, and automatic deployment bootstrap are
> **Unsupported**.

## The decision

The runtime is a current-stage composition mechanism with a durable operational
rule behind it:

```text
deployment owns concrete adapters and credentials
                    |
                    v
runtime owns one explicit in-process composition
                    |
                    v
application services own durable transitions
```

The deployment supplies dependencies; agents and repositories do not construct
their own global dependency graphs. This keeps missing capabilities visible and
prevents a package from quietly becoming an alternate persistence or workflow
owner.

The in-process shape is a current-stage implementation choice. The visible,
fail-closed composition boundary is a durable operational boundary that a future
CLI, service, or worker topology must preserve.

## What `CogniEDARuntime` owns

`CogniEDARuntime` validates and holds one process-local composition. Its
constructor receives:

- a non-empty database URL through `RuntimeConfiguration`;
- an `AuthenticatedPrincipalResolver`;
- a model used by the Hypothesis Analyst;
- one Data Explorer identifier and adapter factory; and
- an executor-context factory.

Construction then:

1. initializes the configured persistence boundary;
2. creates a private `DataExplorerRegistry`;
3. registers exactly the supplied Data Explorer adapter;
4. creates the dispatcher and Hypothesis Analyst;
5. composes one `Planner`; and
6. retains the identity resolver and execution-context factory for runtime
   facades.

The runtime also exposes in-process facades for execution dispatch and
reconciliation, scientific evaluation, governance, Discovery admission, and
validity propagation. Those facades do not transfer transaction ownership to
the runtime. Each operation delegates to its owning application service.

The registry, Planner, and composed Python objects are process-local. Durable
database records can survive process restart, but the runtime object itself does
not. Constructing a new runtime reapplies idempotent SQLite initialization; it
does not automatically start a worker, reclaim every pending operation, or
provide a complete product-level resume loop. Restart-safe orchestration is
therefore **Partially implemented**.

## What `runtime_loader` owns

`load_runtime_from_environment()` is the narrow deployment seam. It reads
`COGNIEDA_RUNTIME_FACTORY`, requires a `module:factory` reference, imports and
calls that factory, and rejects a result that is not a `CogniEDARuntime`.

The loader deliberately does not:

- choose a database URL;
- construct a concrete Data Explorer;
- invent an identity provider;
- select secrets or credentials;
- start a server, worker, or daemon; or
- supply a permissive default when configuration is missing.

The deployment factory owns those choices. The loader mechanism is
**Implemented**, while any particular production factory is
**Unsupported** in this repository.

## Runtime composition is not Planner orchestration

Two application boundaries serve different purposes:

| Boundary | Owns | Does not own |
| --- | --- | --- |
| `application.runtime` and `application.runtime_loader` | dependency assembly, adapter registration, persistence opening, and in-process facades | Planner-operation semantics, scientific transaction write sets, or a product process |
| `application.orchestrator` | approved Planner-operation commit coordination and ordinary workflow persistence | the composition root, deployment adapter selection, or scientific cutover transactions |

`commit_planner_operations` can stage an approved execution bundle in one
application-owned transaction. That makes it a transaction owner for that
write set, not the runtime composition root. Conversely, calling a runtime
facade does not make the runtime the owner of the delegated transaction.

`application.orchestrator` is not the composition root.
`src/application/bootstrap/` has no Python implementation and must not be shown
as a deployed entry point.

## Why the runtime fails closed

Tempting alternatives include building a CLI or HTTP API first, using module
singletons, allowing agents to construct repositories, or letting each package
open its own sessions. Those choices would hide dependency ownership before
the operational topology is known.

The current boundary protects:

- one inspectable composition point;
- explicit failure when required adapters are absent;
- testable dependency injection;
- process-local registries instead of mutable global registration;
- no package-owned global persistence; and
- no hidden application writer created as a side effect of importing an agent
  or repository.

Tests use injected models, principal resolvers, and adapter factories. A test
double proves the boundary can be composed; it is not evidence that a concrete
production adapter exists.

## Costs accepted now

The in-process decision has concrete costs:

- there is no ready-made product interface;
- process isolation and worker scheduling are absent;
- deployments must assemble dependencies manually;
- no deployment identity is supplied by default;
- process-local objects must be reconstructed after restart; and
- recovery methods must be invoked by an external operational loop.

These costs are accepted because choosing a deployment protocol prematurely
would not improve scientific authority or transaction safety.

## Revisit triggers

Revisit the composition mechanism when:

- the first production CLI or API is introduced;
- execution moves to a worker, daemon, or external service;
- multiple users or workspaces must be served concurrently;
- restart recovery becomes an operational service-level requirement;
- credentials and identity resolution move behind a deployment platform; or
- application transactions span separately deployed bounded contexts.

A redesign may replace the in-process object graph. It must preserve explicit
dependency ownership, fail-closed adapter selection, one discoverable route to
each durable transition, and the separation between composition and transaction
authority.

## Related canonical concepts

- [Product bootstrap](product-bootstrap.md)
  owns the unsupported product-process inventory and coherent bootstrap
  prerequisites.
- [Planner operations and approvals](planner-and-approvals.md)
  owns proposal, approval, resume, and commit delegation after composition.
- [Persistence and transactions](persistence-and-transactions.md)
  explains the writers composed behind the runtime.
- [SQLite and portability](sqlite-and-portability.md) defines
  the database qualification that runtime initialization currently enforces.
- [Atomic persistence workflow](atomic-persistence-workflow.md)
  follows one delegated operation through commit or rollback.
- [Design decisions and tradeoffs](../design-decisions/index.md) classifies
  the operational choices without promoting package names into invariants.

## Implementation orientation

The composition source is `src/application/runtime.py`. The deployment-factory
seam is `src/application/runtime_loader.py`. Planner commit coordination is in
`src/application/orchestrator/planner_commit.py`. Focused composition behavior
is exercised by `tests/application/test_runtime_composition.py`.
