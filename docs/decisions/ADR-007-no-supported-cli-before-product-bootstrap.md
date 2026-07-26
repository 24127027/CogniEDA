# ADR-007: No supported CLI before product bootstrap is coherent

**Decision classification:** Durable operational boundary.

**Implementation status:** The in-process runtime and external factory loader
are **Implemented**, and current persistence behavior is **Verified on SQLite**.
A packaged CLI, HTTP API, worker, daemon, and Python product bootstrap are
**Unsupported**.

## Context

CogniEDA already has a substantial in-process application runtime. It composes
database initialization, identity resolution, Planner coordination, executor
registration and dispatch, scientific application services, and
reconciliation. Tests can construct that runtime and call its facades directly.

A product process needs more. It must select a workspace and active research
context, authenticate a principal, configure production analytical adapters,
expose durable approvals, coordinate execution and reconciliation across
restart, and report controlled outcomes. Interface code is therefore part of
the authority and recovery boundary, not merely packaging.

## Problem

A thin CLI or HTTP wrapper would look like a supported product even if its
identity, adapters, approvals, worker lifecycle, restart behavior, and
operational ownership remained undefined. Users and later code would begin to
depend on accidental command syntax and incomplete failure semantics.

The project needs an explicit boundary between library composition that exists
today and a product surface that can make honest end-to-end guarantees.

## Failure mode

If a placeholder surface is shipped as supported, it can:

- run under a test or implicit principal;
- bypass workspace, Objective, session, or frame selection;
- expose an LLM proposal without durable exact approval;
- dispatch work without restart-safe reconciliation;
- lose pending interactions when the process stops;
- imply a concrete Data Explorer or Graph Miner that is not wired;
- report a partial transaction as success; or
- create a second route around canonical scientific transaction owners.

The scientific records might still be protected by lower layers, but the
product would have made false claims about authorization, continuity, and
completion.

## Tempting alternatives

- add a mock command solely to make the repository appear runnable;
- expose the runtime through a placeholder HTTP endpoint;
- start a polling worker without durable supervision or recovery policy;
- treat direct test construction as the supported bootstrap;
- infer provider configuration from development fixtures;
- let `runtime_loader` stand in for authentication and deployment policy; or
- defer authority and restart semantics until after command syntax stabilizes.

## Decision

CogniEDA will not advertise a supported CLI, HTTP API, worker, or daemon until
one coherent product slice preserves the existing authority, transaction,
validity, replay, and recovery boundaries.

`CogniEDARuntime` remains the in-process composition root.
`COGNIEDA_RUNTIME_FACTORY` remains a deployment-supplied factory seam. Neither
is a product process.

The first supported surface may use any appropriate interface shape, but it
must provide production identity, configured analytical adapters, workspace and
session selection, durable approval interaction, execution and reconciliation
coordination, restart recovery, user-visible controlled outcomes, and explicit
operational ownership.

## Invariant protected

A supported interface must preserve the same authority, atomicity, validity,
exact approval, replay, and recovery rules as direct library use. Packaging
cannot create a second scientific writer, weaken Assumption quarantine, treat
retrieval as admissibility, or turn process-local state into durable truth.

## Current implementation

`CogniEDARuntime` accepts an explicit database URL, principal resolver, Analyst
model, Data Explorer identity and factory, and Planner context factory. It
initializes SQLite and composes the current library facades.

`runtime_loader` imports an environment-named `module:factory`, calls it, and
requires a `CogniEDARuntime` result. The deployment remains responsible for
credentials, adapters, workspace policy, and process lifecycle.

The project metadata defines no supported console script. There is no supported
API router, long-running worker, daemon, or Python bootstrap implementation.
`src/application/bootstrap/README.md` is orientation, not executable
bootstrap. The Planner graph module's development rendering helper is not a
product entry point.

Architecture tests enforce the absence of a packaged surface and test-only
production adapters. Runtime tests exercise fail-closed composition and the
factory loader.

## Tradeoffs

Deferral means:

- no immediate supported command-line demo;
- delayed feedback on packaging and interactive approval UX;
- fewer real deployment observations; and
- continued dependence on library and test harnesses for integration evidence.

It also avoids committing to an interface before identity, adapter,
authorization, worker, restart, and recovery semantics are coherent. A future
surface can be designed around the actual authority model rather than preserve
a misleading prototype contract.

## Known limitations

The runtime does not supply production identity, a concrete Data Explorer,
provider credentials, workspace/session discovery, an approval UI, a worker
loop, process supervision, health checks, restart coordination, or a complete
end-to-end product recovery policy.

Durable Planner operations, execution approvals, SessionFrames, runs, outbox,
and inbox records provide useful seams. The default graph checkpointer is
in-memory, and those records do not automatically reconstruct arbitrary node
progress or a complete user conversation.

## Risks

- Product integration feedback may arrive late.
- Deployment-specific factories can diverge without a supported host contract.
- Contributors may mistake direct runtime calls for a production surface.
- An unofficial wrapper may acquire users before its limitations are visible.
- Planner repository coupling may become harder to extract after product
  topology expands.
- Adapter and recovery prerequisites may be implemented independently without
  one coherent acceptance slice.

## Revisit triggers

Revisit this decision when:

- a concrete production Data Explorer exists;
- production identity and authorization exist;
- an Analyst provider is configured by deployment policy;
- durable approval, execution, and reconciliation coordination survives
  restart;
- one end-to-end product slice passes through canonical transaction owners; and
- the proposed interface has explicit security, compatibility, observability,
  and operational ownership.

A second Planner implementation, multiple services or databases, additional
durable approval types, or hard-to-isolate Planner nodes also trigger review of
the Planner application-facade boundary before the surface is supported.

## Consequences for future work

Product work must begin with the complete operational slice, not only command
syntax. It must define the identity and workspace boundary, configure real
scientific adapters, expose exact durable decisions, recover or reconcile
interrupted execution, and report authoritative versus pending outcomes
honestly.

The interface implementation may replace the environment loader or introduce a
service host. It may not weaken canonical transaction ownership, exact
proposal-copy, fail-closed migration, SQLite qualification, protected
evaluation, historical retention, or active validity exclusion.

## Related canonical concepts

- [Product bootstrap](../operations/product-bootstrap.md)
- [Runtime composition](../operations/runtime-composition.md)
- [Planner operations and approvals](../operations/planner-and-approvals.md)
- [SessionFrame scaling and resume limits](../concepts/context/session-frame-scaling.md)
- [Persistence and transactions](../operations/persistence-and-transactions.md)

## Implementation orientation

Runtime composition is in `src/application/runtime.py`; factory loading is in
`src/application/runtime_loader.py`; bootstrap orientation is in
`src/application/bootstrap/README.md`; and project entry-point metadata is in
`pyproject.toml`. Product-surface enforcement is in
`tests/architecture/test_architecture_enforcement.py`, with runtime behavior in
`tests/application/test_runtime_composition.py`.
