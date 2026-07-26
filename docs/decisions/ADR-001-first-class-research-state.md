# ADR-001: First-Class research state

**Decision classification:** Foundational invariant.

**Implementation status:** **Implemented** for the current schema, persistence,
and supported application boundaries. Scientific-payload immutability is not a
universal database constraint.

## Context

CogniEDA must carry analytical work across sessions without allowing summaries,
chat history, or operational records to become scientific knowledge by
accident. A durable row is not authoritative merely because it is persistent.
Research intent, data identity, workflow, test contracts, observations, claims,
and user-governed context need different schemas and lifecycle rules.

## Problem

Generic memory cannot answer which dataset version a result used, whether a
claim is still active, which decision rule authorized it, or whether a record is
knowledge, workflow, provenance, cache, or presentation. If those distinctions
are implicit, downstream code can retrieve the wrong state into reasoning and
launder an operational artifact into scientific authority.

## Failure mode

A chat summary merges incompatible scopes, a mutable dataset label silently
changes beneath existing Evidence, a completed Task is treated as a finding, or
a generated answer is retrieved as an established claim. The user can no longer
trace a conclusion to one bounded analytical path.

## Tempting alternatives

- preserve raw conversations as the primary memory;
- store all durable entities in one generic object graph;
- treat every persisted table as a First-Class Object;
- use vector retrieval as both storage and authority; or
- promote Workspace, Question, AnalysisFrame, PlannerOperation, ExecutionRun,
  GeneratedView, or cache entries into scientific identity.

These approaches reduce schema work but erase the boundaries that make research
state auditable.

## Decision

CogniEDA defines exactly eight First-Class Objects:

1. `Objective`;
2. `DataProfile`;
3. `Assumption`;
4. `Task`;
5. `Hypothesis`;
6. `Evidence`;
7. `Discovery`; and
8. `SessionFrame`.

`Workspace` is a filesystem and runtime boundary. A user `Question` is
transient input that becomes workflow state. `AnalysisFrame`, `PlannerOperation`,
and `ExecutionRun` are provenance or workflow records. `GeneratedView` is a
presentation/provenance result. `EvidenceCacheEntry` is cache state.
`ValidityEvent` is an immutable audit event. None is an FCO.

Each FCO has one epistemic role:

- `Objective` preserves research intent;
- immutable `DataProfile` identifies one dataset version;
- `Assumption` records a planning premise that is not empirical evidence;
- `Task` is governed workflow state;
- `Hypothesis` is one bounded analytical test contract;
- immutable `Evidence` records observations;
- immutable `Discovery` records an evidence-bound claim; and
- `SessionFrame` governs reconstructable active context.

Exactly-one relationships apply only on the successful terminal analytical
path. One eligible terminal analytical Task can own at most one Hypothesis, and
one Hypothesis can own at most one Discovery. Rejection, cancellation, technical
failure, or incomplete work may correctly produce neither. Parent Tasks do not
produce Hypotheses or Discoveries; their future synthesis output is a
`GeneratedView`, not knowledge.

## Invariant protected

Persistence cannot grant scientific authority. Every admitted conclusion
remains typed, scope-bounded, evidence-bound, and traceable to a specific
dataset identity and analytical contract.

## Current implementation

The exact FCO enumeration is defined in `src/schemas/enums.py`. FCO schemas live
under `src/schemas/research/`, `src/schemas/evidence/`, and
`src/schemas/discovery/`; persistence models live under `src/db/models/`.
Repository and application services implement the supported lifecycle.

`DataProfile`, `Evidence`, and `Discovery` use frozen validation models.
Supported repositories are append-oriented and do not expose scientific-payload
updates for them. Database uniqueness plus repository and application guards
enforce terminal Task-to-Hypothesis and Hypothesis-to-Discovery cardinality on
the supported path.

## Tradeoffs

Typed state adds schemas, migrations, validators, repositories, and explicit
transitions. New concepts cannot be introduced by adding an arbitrary blob.
The benefit is that retrieval, governance, and validity can reason about
authority rather than only semantic similarity.

## Known limitations

- Direct ORM or SQL access can bypass supported repository and application
  boundaries; the database does not universally freeze every scientific payload.
- The complete parent-Task `GeneratedView` workflow is a **Design target**.
- Product bootstrap, complete planner branches, and end-to-end resume
  experiences are **Unsupported**.
- Some operational contracts remain split across an FCO and its governed
  workflow record rather than stored on one row.

## Risks

The most serious risk is ontology drift: a convenient new durable record may be
mistaken for knowledge. Another risk is overstating validation-model freezing as
database-wide immutability. Both would make implementation claims stronger than
the supported boundary.

## Revisit triggers

Revisit mechanisms when storage backends, multi-tenant boundaries, or scale
requirements change. Revisit the exact FCO set only if a proposed object has a
distinct epistemic identity, lifecycle, authority source, and retrieval role
that cannot be represented as workflow, provenance, cache, filesystem state, or
generated output. Convenience alone is not a trigger.

## Consequences for future work

Every new durable entity must be classified before implementation. Schema and
repository changes must preserve immutability and cardinality invariants.
Generated presentation must remain outside scientific authority, and migrations
must preserve existing object identity rather than silently reinterpret it.

## Related canonical concepts

- [Design decisions and tradeoffs](../design-decisions/index.md)
- [Research-state objects and roles](../concepts/research-state/objects-and-roles.md)
- [Investigation lifecycle](../concepts/research-state/investigation-lifecycle.md)
- [Context continuity and resume](../concepts/context/continuity-and-resume.md)

## Implementation orientation

Start with `src/schemas/enums.py`, `src/schemas/research/`,
`src/schemas/evidence/`, `src/schemas/discovery/`, `src/db/models/`, and
`src/repositories/`. Boundary and cardinality checks are concentrated under
`tests/architecture/`, `tests/repositories/`, `tests/application/`, and
`tests/e2e/`.
