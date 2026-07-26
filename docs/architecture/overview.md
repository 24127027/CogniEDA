# System Architecture Overview

> **Implementation status:** **Partially implemented**; persistence and guarded
> transactions are **Verified on SQLite**.

The canonical maturity summary is
[CogniEDA current state](../current-state.md), and future dependencies belong
to the [dependency-driven roadmap](../roadmap.md). This page owns the compact
technical architecture view.

Reader-first concept owners:
[Scientific authority](../scientific-authority.md),
[Protected evaluation context](../protected-evaluation-context.md), and
[Governance and Discovery admission](../governance-and-discovery-admission.md),
[Planner boundary and operation model](../planner-boundary-and-operation-model.md),
[SessionFrame and active context](../session-frame-and-active-context.md),
[Retrieval and context type safety](../retrieval-and-context-type-safety.md),
[Retrieval strategy and scaling](../retrieval-strategy-and-scaling.md),
[Context reconstruction and continuity](../context-reconstruction-and-continuity.md),
[SessionFrame scaling and resume boundary](../session-frame-scaling-and-resume-boundary.md),
[Validity over time](../validity-over-time.md),
[Atomic validity propagation](../atomic-validity-propagation.md),
[Runtime and composition boundary](../runtime-and-composition-boundary.md),
[Product surface and bootstrap boundary](../product-surface-and-bootstrap-boundary.md),
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

Planner answer, suggestion, result-review, conflict-review, durable graph
pause/resume, and project-closure paths are not complete. The current Planner
opens repository sessions directly, but its generic commit fails closed for
Evidence, Discovery, and protected terminal scientific transitions.

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
