# System Architecture Overview

> **Implementation status:** **Partially implemented**; persistence and guarded
> transactions are **Verified on SQLite**.

Reader-first concept owners:
[Scientific authority](../scientific-authority.md),
[Protected evaluation context](../protected-evaluation-context.md), and
[Governance and Discovery admission](../governance-and-discovery-admission.md),
[SessionFrame and active context](../session-frame-and-active-context.md),
[Retrieval and context type safety](../retrieval-and-context-type-safety.md),
[Context reconstruction and continuity](../context-reconstruction-and-continuity.md),
[Validity over time](../validity-over-time.md), and
[Atomic validity propagation](../atomic-validity-propagation.md),
[Runtime and composition boundary](../runtime-and-composition-boundary.md),
[Persistence and transaction ownership](../persistence-and-transaction-ownership.md),
and [SQLite boundary and portability](../sqlite-boundary-and-portability.md).
This page remains a source-oriented architecture summary.

CogniEDA is validity-preserving research-state infrastructure for governed analytical
investigation. Its priority order is:

1. conclusion validity and traceability;
2. context type safety;
3. multi-session continuity.

## Current implementation

The checked-in system is an in-process Python runtime, not a product service:

```text
Planner and deployment adapters
        |
        v
application transaction and coordination services
        |
        +--> observation-only Data Explorer adapter boundary
        +--> protected Hypothesis Analyst boundary
        |
        v
schemas -> repositories -> db.models facade -> workspace-local SQLite
```

Implemented paths include approval-gated Planner operations, fenced execution attempts,
AnalysisFrame/Evidence admission, protected evaluation, durable governance decisions, atomic
Discovery admission, validity propagation, bounded Discovery retrieval, and SessionFrame
snapshots.

## Target design and unsupported surfaces

**Design target:** The broader product workflow adds interactive entry points, concrete production
adapters, executable dataset versioning, and more complete retrieval.

**Unsupported:** No checked-in CLI, HTTP/gRPC service, worker daemon, production Data Explorer,
production authentication resolver, or default Hypothesis Analyst model provider exists.
Graph Miner and the event/bootstrap package directories are scaffold or documentation-only.

## Load-bearing boundaries

- Data Explorer returns observations; it does not evaluate or persist.
- Hypothesis Analyst alone authors `DiscoveryProposal` scientific wording from a closed bundle.
- Application services own durable transitions; repositories are persistence adapters.
- `AtomicDiscoveryAdmissionService` is the only supported Discovery materializer.
- `AtomicValidityPropagationService` is the only supported validity-event transaction owner.
- SQLite is the only verified database boundary.

See [Scientific Specialist Contracts](scientific-specialist-contracts.md),
[Persistence and Transactions](persistence-and-transactions.md), and
[Structural Exit Status](structural-exit-status.md).
