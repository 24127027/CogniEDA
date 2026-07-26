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
3. [CogniEDA current state](current-state.md) states the canonical maturity
   boundary: what works in process, what remains partial, and what is
   unsupported.
4. [Capability and maturity map](capability-and-maturity-map.md) compares the
   implemented infrastructure, incomplete workflows, known deviations, and
   product consequences by domain.
5. [Dependency-driven roadmap](roadmap.md) classifies the blockers and
   observable exit criteria for one coherent product slice and later
   trigger-based work.

### Research-state model

1. [Research-state objects and roles](concepts/research-state/objects-and-roles.md) explains the durable objects,
   non-FCO records, epistemic roles, lifecycle rules, and cardinality limits.
2. [Investigation lifecycle](concepts/research-state/investigation-lifecycle.md) follows one
   investigation end to end, showing where authority changes hands, where the
   user governs, and when state becomes durable.

### Scientific lifecycle

1. [Scientific authority](concepts/scientific-lifecycle/scientific-authority.md) explains why observation,
   evaluation, governance, and materialization must remain separate.
2. [Protected evaluation](concepts/scientific-lifecycle/protected-evaluation.md) distinguishes
   planning context from the closed repository-built input allowed to support a
   scientific proposal.
3. [Discovery governance and admission](concepts/scientific-lifecycle/discovery-governance-and-admission.md)
   explains exact authorization, proposal-copy, atomic admission, replay,
   fencing, conflict, and the SQLite verification boundary.
4. [Execution to Discovery](concepts/scientific-lifecycle/execution-to-discovery.md) applies those
   mechanisms to the running example from an approved analytical Task through
   durable Discovery.

### Validity over time

1. [Validity over time](concepts/validity/validity-over-time.md) explains why historical
   truth-to-record and current scientific authority must remain distinct.
2. [Atomic validity propagation](concepts/validity/validity-propagation.md) reconstructs
   the authorized command, fingerprints, deterministic plan, atomic write set,
   replay, conflicts, and SQLite concurrency boundary.
3. [Active retrieval after invalidation](concepts/validity/active-retrieval-after-invalidation.md)
   connects committed lifecycle changes to active exclusion, historical reads,
   pins, stale frames, and context-freshness limits.
4. [From validity change to active context](concepts/validity/validity-change-to-active-context.md)
   follows the running example from an Evidence defect through later
   repository-current context.

### Context, retrieval, and continuity

1. [SessionFrame and active context](concepts/context/session-frame.md)
   explains user-governed context selection, append-oriented snapshots, pins,
   exclusions, and the limits of frame authority.
2. [Context type safety and retrieval](concepts/context/context-type-safety.md)
   reconstructs the validity-first retrieval boundary, current deterministic
   ranking, context modes, and known scope limitations.
3. [Retrieval strategy](concepts/context/retrieval-strategy.md) explains
   the structural candidate pipeline, lexical ranking, result budget,
   revalidation limits, semantic deferral, and scaling triggers.
4. [Context continuity and resume](concepts/context/continuity-and-resume.md)
   separates durable research-state continuity from complete product-level
   session resume.
5. [SessionFrame scaling and resume limits](concepts/context/session-frame-scaling.md)
   distinguishes frame succession and durable workflow records from
   database-global selection and in-memory graph checkpointing.
6. [Building active context from research state](concepts/context/building-active-context.md)
   applies those mechanisms to the running example.

### Operational architecture

1. [Planner operations and approvals](operations/planner-and-approvals.md)
   separates request coordination, durable proposals, approval, resume, and
   commit delegation from scientific authority.
2. [Operation approval workflows](operations/operation-approval-workflows.md)
   follows ordinary Task management and fresh execution-contract approval from
   raw request through commit or fail-closed revalidation.
3. [Runtime composition](operations/runtime-composition.md)
   explains the in-process composition root, deployment-supplied dependencies,
   runtime loader, and absent product surfaces.
4. [Product bootstrap](operations/product-bootstrap.md)
   separates the in-process library runtime from unsupported product processes
   and defines the minimum coherent integration slice.
5. [Persistence and transactions](operations/persistence-and-transactions.md)
   separates schemas, repositories, physical models, and migrations while
   identifying the application owners of atomic durable changes.
6. [SQLite and portability](operations/sqlite-and-portability.md) states
   what is verified today, which mechanisms are SQLite-specific, and what
   another backend would need to prove.
7. [SQLite initialization and migrations](operations/sqlite-and-migrations.md)
   follows fresh initialization, existing-database upgrade, trigger
   installation, migration-history policy, and legacy quarantine.
8. [Atomic persistence workflow](operations/atomic-persistence-workflow.md)
   applies those operational boundaries to one exact-copy Discovery-admission
   transaction.

### Design decisions

1. [Design decisions and tradeoffs](design-decisions/index.md) explains
   which boundaries are foundational or durable, which mechanisms are
   temporary, what they cost, and what future redesigns must preserve. Its
   decision-record links provide detail without interrupting the conceptual
   tracks.

Together these thirty pages form the current canonical project
explanation. Problem, mental model, authority, validity, and context precede
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

The repository also retains architecture and workflow technical references,
decision records, development guides, and package READMEs created before this
narrative foundation. They remain useful implementation references, but they
are not the canonical reading sequence. Those documents are classified as
contributor guidance, design-decision records, technical references, agent
instructions, or the legacy transition surface. Canonical pages own concepts;
retained references own only their source-level mechanics. Source code and
tests remain the authority for current behavior.

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

## Documentation maintenance boundaries

- Contributor code orientation, package navigation, transaction-owner maps,
  focused-test locations, and change guidance belong in the separate
  contributor layer.
- Retained technical references have already been classified and linked to
  their concept and contributor owners. Future consolidation, relocation, or
  retirement still requires unique-content and inbound-link review.
- Checkout-specific documentation verification belongs in ignored local audit
  records. Product work remains governed by the dependency and invariant
  boundaries in the roadmap.

These are documentation ownership rules, not claims that the corresponding
product workflows are implemented.
