# CogniEDA documentation

CogniEDA's documentation explains how an analytical investigation can remain
traceable, valid within scope, and resumable without turning conversation into
scientific authority. It is written for researchers, product and engineering
contributors, reviewers, and project owners who may know nothing about the
repository.

The canonical thesis is:

> CogniEDA is validity-preserving research-state infrastructure.

## Recommended reading journey

Read the Phase 1 foundation in this order:

1. [What is CogniEDA?](what-is-cognieda.md) introduces the practical problem,
   the project thesis, the running example, and the current maturity boundary.
2. [Problem and thesis](problem-and-thesis.md) examines the failure modes that
   motivate governed research state and the tradeoffs of the design response.
3. [Research-state model](research-state-model.md) explains the durable objects,
   non-FCO records, epistemic roles, lifecycle rules, and cardinality limits.
4. [From question to Discovery](from-question-to-discovery.md) follows one
   investigation end to end, showing where authority changes hands, where the
   user governs, and when state becomes durable.

Together these pages form the canonical Phase 1 project explanation. They are
concept-first: problem, mental model, investigation, and governing principles
come before packages or symbols.

## Project understanding and source orientation

The four documents above are the recommended path for understanding CogniEDA.
They use implementation references only as optional verification aids.

The repository also retains architecture pages, workflow pages, decision
records, development guides, and package READMEs created before this narrative
foundation. They remain useful implementation reference, but they are not the
canonical reading sequence for Phase 1. Later S4.1 phases will reconcile,
rewrite, merge, or relocate them without discarding source-grounded detail.
Until that work is complete, source code and tests remain the authority for
current behavior.

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

## Later documentation phases

The following narrative layers are intentionally not complete in Phase 1:

- **Phase 2:** scientific authority, protected context, memory, SessionFrame
  governance, retrieval, invalidation, and validity propagation;
- **Phase 3:** architectural decisions, alternatives, tradeoffs, risks, scaling
  boundaries, and redesign triggers;
- **Phase 4:** current-state detail, roadmap, package-level code orientation,
  and relocation or retirement of stale implementation reference;
- **Phase 5:** adversarial consistency review across terminology, links, status
  claims, source, and tests.

These are future sections, not links to documents that do not yet exist.
