# CogniEDA documentation

CogniEDA's documentation explains how an analytical investigation can remain
traceable, valid within scope, and resumable without turning conversation into
scientific authority. It is written for researchers, product and engineering
contributors, reviewers, and project owners who may know nothing about the
repository.

The canonical thesis is:

> CogniEDA is validity-preserving research-state infrastructure.

## Recommended reading journey

Read the canonical narrative in this order:

1. [What is CogniEDA?](what-is-cognieda.md) introduces the practical problem,
   the project thesis, the running example, and the current maturity boundary.
2. [Problem and thesis](problem-and-thesis.md) examines the failure modes that
   motivate governed research state and the tradeoffs of the design response.
3. [Research-state model](research-state-model.md) explains the durable objects,
   non-FCO records, epistemic roles, lifecycle rules, and cardinality limits.
4. [From question to Discovery](from-question-to-discovery.md) follows one
   investigation end to end, showing where authority changes hands, where the
   user governs, and when state becomes durable.
5. [Design decisions and tradeoffs](design-decisions-and-tradeoffs.md) explains
   why the core epistemic boundaries exist, which are foundational, what they
   cost, and what future redesigns must preserve.
6. [Scientific authority](scientific-authority.md) explains why observation,
   evaluation, governance, and materialization must remain separate.
7. [Protected evaluation context](protected-evaluation-context.md) distinguishes
   planning context from the closed repository-built input allowed to support a
   scientific proposal.
8. [Governance and Discovery admission](governance-and-discovery-admission.md)
   explains exact authorization, proposal-copy, atomic admission, replay,
   fencing, conflict, and the SQLite verification boundary.
9. [From execution to Discovery](from-execution-to-discovery.md) applies those
   three mechanisms to the running example from an approved analytical Task
   through durable Discovery.
10. [SessionFrame and active context](session-frame-and-active-context.md)
   explains user-governed context selection, append-oriented snapshots, pins,
   exclusions, and the limits of frame authority.
11. [Retrieval and context type safety](retrieval-and-context-type-safety.md)
    reconstructs the validity-first retrieval boundary, current deterministic
    ranking, context modes, and known scope limitations.
12. [Context reconstruction and continuity](context-reconstruction-and-continuity.md)
    separates durable research-state continuity from complete product-level
    session resume.
13. [From research state to active context](from-research-state-to-active-context.md)
    applies those mechanisms to the running churn example.
14. [Validity over time](validity-over-time.md) explains why historical
    truth-to-record and current scientific authority must remain distinct.
15. [Atomic validity propagation](atomic-validity-propagation.md) reconstructs
    the authorized command, fingerprints, deterministic plan, atomic write set,
    replay, conflicts, and SQLite concurrency boundary.
16. [Invalidation and active retrieval](invalidation-and-active-retrieval.md)
    connects committed lifecycle changes to active exclusion, historical reads,
    pins, stale frames, and context-freshness limits.
17. [From validity change to reconstructed context](from-validity-change-to-reconstructed-context.md)
    follows the running churn example from an Evidence defect through later
    repository-current context.
18. [Runtime and composition boundary](runtime-and-composition-boundary.md)
    explains the in-process composition root, deployment-supplied dependencies,
    runtime loader, and absent product surfaces.
19. [Persistence and transaction ownership](persistence-and-transaction-ownership.md)
    separates schemas, repositories, physical models, and migrations while
    identifying the application owners of atomic durable changes.
20. [SQLite boundary and portability](sqlite-boundary-and-portability.md)
    states what is verified today, which mechanisms are SQLite-specific, and
    what another backend would need to prove.
21. [Database initialization and migrations](database-initialization-and-migrations.md)
    follows fresh initialization, existing-database upgrade, trigger
    installation, immutable migration history, and legacy quarantine.
22. [From runtime composition to atomic persistence](from-runtime-composition-to-atomic-persistence.md)
    applies those operational boundaries to one exact-copy Discovery-admission
    transaction.

Together these pages form the current canonical project explanation. They are
concept-first: problem, mental model, investigation, authority, protected
context, governance, admission, active context, retrieval, temporal validity,
and continuity come before packages or symbols.

## Project understanding and source orientation

The twenty-two documents above are the recommended path for understanding CogniEDA.
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

## Deferred narrative areas

The following narrative areas are intentionally not complete here:

- **Deferred:** remaining operational decisions about Planner persistence
  coupling, retrieval mechanisms, product bootstrap, deployment authentication,
  distributed execution, and product-surface timing;
- **Deferred:** current-state detail, roadmap, package-level code orientation,
  and relocation or retirement of stale implementation reference;
- **Deferred:** adversarial consistency review across terminology, links, status
  claims, source, and tests.

These are future sections, not claims that the corresponding product workflows
are implemented.
