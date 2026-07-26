# Runtime composition

> **Role:** Technical reference. **Canonical concept owner:**
> [Runtime composition](../../operations/runtime-composition.md).
> **Contributor entry:** [Contributor documentation](../../development/index.md).
> **Current-state owner:** [CogniEDA current state](../../current-state.md).

> **Implementation status:** in-process composition **Implemented**; production
> bootstrap **Unsupported**; database semantics **Verified on SQLite**.

The reader-facing rationale and deployment boundary are owned by
[Runtime composition](../../operations/runtime-composition.md).
Unsupported product processes and bootstrap prerequisites are owned by
[Product bootstrap](../../operations/product-bootstrap.md).
This page retains source-level composition orientation.

## Current implementation

`CogniEDARuntime` is defined in `src/application/runtime.py`. Construction:

1. requires an explicit SQLite database URL;
2. calls `init_db`;
3. requires an `AuthenticatedPrincipalResolver`;
4. requires a Hypothesis Analyst model;
5. creates a private `DataExplorerRegistry` and registers exactly one supplied adapter factory;
6. creates a no-tool Hypothesis Analyst agent and one database-bound Planner.

The runtime exposes:

- Planner access;
- Data Explorer dispatch and execution reconciliation;
- protected evaluation enqueue/run;
- authenticated authority issuance and proposal decision recording;
- authenticated Discovery admission coordination;
- validity propagation.

Each method opens a fresh session from the one configured database URL. Durable outbox/inbox,
evaluation control, admission claims, and validity events allow services to reconstruct work after
process restart. The runtime object, registry, and Planner are process-local, and
there is no automatic background loop.

## Deployment boundary

`runtime_loader.load_runtime_from_environment` requires
`COGNIEDA_RUNTIME_FACTORY=module:factory`; it does not supply default production adapters.
The `src/application/bootstrap/` directory contains no Python implementation.
`application.orchestrator` coordinates approved Planner-operation commits; it
is not the composition root.

## Unsupported surfaces

**Unsupported:** The repository has no packaged CLI, HTTP/gRPC API, daemon, worker process,
authentication implementation, production Data Explorer, or default production model provider.
Tests and direct Python calls are not product entry points.
