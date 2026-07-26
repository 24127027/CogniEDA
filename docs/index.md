# CogniEDA documentation

CogniEDA's documentation explains how an analytical investigation can remain
traceable, valid within scope, and resumable without turning conversation into
scientific authority. It is written for researchers, product and engineering
contributors, reviewers, and project owners who may know nothing about the
repository.

The canonical thesis is:

> CogniEDA is validity-preserving research-state infrastructure.

## Recommended reading journey

Follow the tracks in order. Within a track, read top to bottom.

### Start here

1. [What is CogniEDA?](what-is-cognieda.md) introduces the practical problem,
   the project thesis, the running example, and the current maturity boundary.
2. [Problem and thesis](problem-and-thesis.md) examines the failure modes that
   motivate governed research state and the tradeoffs of the design response.

### Current state and roadmap

1. [CogniEDA current state](current-state.md) states the canonical maturity
   boundary: what works in process, what remains partial, and what is
   unsupported.
2. [Capability and maturity map](capability-and-maturity-map.md) compares the
   implemented infrastructure, incomplete workflows, known deviations, and
   product consequences by domain.
3. [Dependency-driven roadmap](roadmap.md) classifies the blockers and
   observable exit criteria for one coherent product slice and later
   trigger-based work.

### Research-state model

1. [Research-state model](research-state-model.md) explains the durable objects,
   non-FCO records, epistemic roles, lifecycle rules, and cardinality limits.
2. [From question to Discovery](from-question-to-discovery.md) follows one
   investigation end to end, showing where authority changes hands, where the
   user governs, and when state becomes durable.

### Scientific validity and authority

1. [Scientific authority](scientific-authority.md) explains why observation,
   evaluation, governance, and materialization must remain separate.
2. [Protected evaluation context](protected-evaluation-context.md) distinguishes
   planning context from the closed repository-built input allowed to support a
   scientific proposal.
3. [Governance and Discovery admission](governance-and-discovery-admission.md)
   explains exact authorization, proposal-copy, atomic admission, replay,
   fencing, conflict, and the SQLite verification boundary.
4. [From execution to Discovery](from-execution-to-discovery.md) applies those
   mechanisms to the running example from an approved analytical Task through
   durable Discovery.
5. [Validity over time](validity-over-time.md) explains why historical
   truth-to-record and current scientific authority must remain distinct.
6. [Atomic validity propagation](atomic-validity-propagation.md) reconstructs
   the authorized command, fingerprints, deterministic plan, atomic write set,
   replay, conflicts, and SQLite concurrency boundary.
7. [Invalidation and active retrieval](invalidation-and-active-retrieval.md)
   connects committed lifecycle changes to active exclusion, historical reads,
   pins, stale frames, and context-freshness limits.
8. [From validity change to reconstructed context](from-validity-change-to-reconstructed-context.md)
   follows the running example from an Evidence defect through later
   repository-current context.

### Context, retrieval, and continuity

1. [SessionFrame and active context](session-frame-and-active-context.md)
   explains user-governed context selection, append-oriented snapshots, pins,
   exclusions, and the limits of frame authority.
2. [Retrieval and context type safety](retrieval-and-context-type-safety.md)
   reconstructs the validity-first retrieval boundary, current deterministic
   ranking, context modes, and known scope limitations.
3. [Retrieval strategy and scaling](retrieval-strategy-and-scaling.md) explains
   the structural candidate pipeline, lexical ranking, result budget,
   revalidation limits, semantic deferral, and scaling triggers.
4. [Context reconstruction and continuity](context-reconstruction-and-continuity.md)
   separates durable research-state continuity from complete product-level
   session resume.
5. [SessionFrame scaling and resume boundary](session-frame-scaling-and-resume-boundary.md)
   distinguishes frame succession and durable workflow records from
   database-global selection and in-memory graph checkpointing.
6. [From research state to active context](from-research-state-to-active-context.md)
   applies those mechanisms to the running example.

### Operational architecture

1. [Planner boundary and operation model](planner-boundary-and-operation-model.md)
   separates request coordination, durable proposals, approval, resume, and
   commit delegation from scientific authority.
2. [From user request to approved operation](from-user-request-to-approved-operation.md)
   follows ordinary Task management and fresh execution-contract approval from
   raw request through commit or fail-closed revalidation.
3. [Runtime and composition boundary](runtime-and-composition-boundary.md)
   explains the in-process composition root, deployment-supplied dependencies,
   runtime loader, and absent product surfaces.
4. [Product surface and bootstrap boundary](product-surface-and-bootstrap-boundary.md)
   separates the in-process library runtime from unsupported product processes
   and defines the minimum coherent integration slice.
5. [Persistence and transaction ownership](persistence-and-transaction-ownership.md)
   separates schemas, repositories, physical models, and migrations while
   identifying the application owners of atomic durable changes.
6. [SQLite boundary and portability](sqlite-boundary-and-portability.md) states
   what is verified today, which mechanisms are SQLite-specific, and what
   another backend would need to prove.
7. [Database initialization and migrations](database-initialization-and-migrations.md)
   follows fresh initialization, existing-database upgrade, trigger
   installation, migration-history policy, and legacy quarantine.
8. [From runtime composition to atomic persistence](from-runtime-composition-to-atomic-persistence.md)
   applies those operational boundaries to one exact-copy Discovery-admission
   transaction.

### Design decisions

1. [Design decisions and tradeoffs](design-decisions-and-tradeoffs.md) explains
   which boundaries are foundational or durable, which mechanisms are
   temporary, what they cost, and what future redesigns must preserve. Its ADR
   links provide decision detail without interrupting the conceptual tracks.

Together these thirty pages form the current canonical project
explanation. Problem, mental model, authority, context, and validity precede
runtime and persistence detail; repository symbols remain optional
implementation orientation.

## Contributor documentation

The canonical journey above explains what CogniEDA means. The separate
contributor layer explains where the current implementation lives and which
tests protect a change; it is not part of the thirty-page conceptual journey.

- [Contributor hub](development/index.md)
- [Code orientation](development/code-orientation.md)
- [Change-boundary guide](development/change-boundary-guide.md)
- [Testing strategy](development/testing.md)
- [Development setup](development/setup.md)

## Project understanding and source orientation

The thirty documents above are the recommended path for understanding CogniEDA.
They use implementation references only as optional verification aids.

The repository also retains architecture pages, workflow pages, decision
records, development guides, and package READMEs created before this narrative
foundation. They remain useful implementation reference, but they are not the
canonical reading sequence. Later documentation work will reconcile, rewrite,
merge, or relocate them without discarding source-grounded detail. Until that
work is complete, source code and tests remain the authority for current
behavior.

## Implementation-status vocabulary

Every implementation claim in the canonical narrative uses these meanings:

| Label | Meaning |
| --- | --- |
| **Implemented** | The behavior exists on a supported source path. |
| **Verified on SQLite** | The behavior is implemented and tested on SQLite; no cross-database guarantee is claimed. |
| **Partially implemented** | Some required behavior exists, but the complete user-facing or operational workflow does not. |
| **Design target** | The architecture intends to support the behavior, but current source does not provide it. |
| **Deferred** | The work is intentionally postponed to a later package or documentation phase. |
| **Known deviation** | Current source differs from the preferred long-term boundary and the difference is accepted temporarily. |
| **Unsupported** | No supported product surface currently exists. |

A schema, protocol, directory, injected interface, or test fixture is not enough
by itself to make a feature **Implemented**.

## Documentation follow-up boundaries

- **Phase 4B:** contributor code orientation, package navigation,
  transaction-owner maps, focused-test locations, and change guidance are now
  provided in the separate contributor layer.
- **Deferred to Phase 4C:** technical-reference consolidation, duplicate
  removal, redirects, file relocation, and link migration after unique content
  and inbound links are accounted for.
- **Deferred to Phase 5:** final documentation-system review follows Phase 4C;
  product work remains governed by the dependency and invariant boundaries in
  the roadmap.

These are future documentation or product responsibilities, not claims that
the corresponding workflows are implemented.
