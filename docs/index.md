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
5. [Scientific authority](scientific-authority.md) explains why observation,
   evaluation, governance, and materialization must remain separate.
6. [Protected evaluation context](protected-evaluation-context.md) distinguishes
   planning context from the closed repository-built input allowed to support a
   scientific proposal.
7. [Governance and Discovery admission](governance-and-discovery-admission.md)
   explains exact authorization, proposal-copy, atomic admission, replay,
   fencing, conflict, and the SQLite verification boundary.
8. [From execution to Discovery](from-execution-to-discovery.md) applies those
   three mechanisms to the running example from an approved analytical Task
   through durable Discovery.
9. [SessionFrame and active context](session-frame-and-active-context.md)
   explains user-governed context selection, append-oriented snapshots, pins,
   exclusions, and the limits of frame authority.
10. [Retrieval and context type safety](retrieval-and-context-type-safety.md)
    reconstructs the validity-first retrieval boundary, current deterministic
    ranking, context modes, and known scope limitations.
11. [Context reconstruction and continuity](context-reconstruction-and-continuity.md)
    separates durable research-state continuity from complete product-level
    session resume.
12. [From research state to active context](from-research-state-to-active-context.md)
    applies those mechanisms to the running churn example.

Together these pages form the current canonical project explanation. They are
concept-first: problem, mental model, investigation, authority, protected
context, governance, admission, active context, retrieval, and continuity come
before packages or symbols.

## Project understanding and source orientation

The twelve documents above are the recommended path for understanding CogniEDA.
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

- **Deferred:** the complete validity-over-time narrative, including source
  fingerprints, affected-object planning, atomic propagation, replay,
  concurrency, and long-term continuity after authority changes;
- **Deferred:** broader architectural decisions, alternatives, risks, scaling
  boundaries, and redesign triggers;
- **Deferred:** current-state detail, roadmap, package-level code orientation,
  and relocation or retirement of stale implementation reference;
- **Deferred:** adversarial consistency review across terminology, links, status
  claims, source, and tests.

These are future sections, not claims that the corresponding product workflows
are implemented.
