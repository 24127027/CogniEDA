# System overview

> **Role:** Technical reference. **Canonical concept owner:**
> [Runtime composition](../../operations/runtime-composition.md).
> **Contributor entry:** [Contributor documentation](../../development/index.md).
> **Current-state owner:** [CogniEDA current state](../../current-state.md).

> **Local implementation qualification:** the source-oriented mechanics below
> are in-process and their guarded persistence behavior is **Verified on SQLite**.
> The project-wide maturity account belongs to the current-state owner below.

The canonical maturity summary is
[CogniEDA current state](../../current-state.md), and future dependencies belong
to the [dependency-driven roadmap](../../roadmap.md). This page owns the compact
technical architecture view.

Reader-first concept owners:
[Scientific authority](../../concepts/scientific-lifecycle/scientific-authority.md),
[Protected evaluation](../../concepts/scientific-lifecycle/protected-evaluation.md), and
[Discovery governance and admission](../../concepts/scientific-lifecycle/discovery-governance-and-admission.md),
[Planner operations and approvals](../../operations/planner-and-approvals.md),
[SessionFrame and active context](../../concepts/context/session-frame.md),
[Context type safety and retrieval](../../concepts/context/context-type-safety.md),
[Retrieval strategy](../../concepts/context/retrieval-strategy.md),
[Context continuity and resume](../../concepts/context/continuity-and-resume.md),
[SessionFrame scaling and resume limits](../../concepts/context/session-frame-scaling.md),
[Validity over time](../../concepts/validity/validity-over-time.md),
[Atomic validity propagation](../../concepts/validity/validity-propagation.md),
[Runtime composition](../../operations/runtime-composition.md),
[Product bootstrap](../../operations/product-bootstrap.md),
[Persistence and transactions](../../operations/persistence-and-transactions.md),
and [SQLite and portability](../../operations/sqlite-and-portability.md).
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

See [Scientific component contracts](scientific-component-contracts.md),
[Transaction write sets](transaction-write-sets.md), and
[Implemented boundaries](implemented-boundaries.md).
