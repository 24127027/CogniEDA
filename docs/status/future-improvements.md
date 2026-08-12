# Future improvements

Future work must preserve the priority order: validity and traceability first,
context type safety second, continuity third, then speed and convenience. This
page classifies direction; it does not promise delivery dates or sequencing.

## Frozen design targets

These are established architecture, not speculative enhancements:

- preserve the canonical `DATA`, `SCIENTIFIC`, and `GRAPH` Task kinds while
  keeping Planner response synthesis outside Task execution and keeping Task
  identity separate from PlanRevision capability, dependency, and coordination
  metadata;
- integrate the implemented PlanRevision V1 domain and pure validator plus the
  SQLite repository foundation with Planner authoring, human approval, exact
  post-approval validation and persistence, active revision selection,
  activation, and Task DAG runtime;
- preserve Planner-only human interaction while preventing Planner ownership
  of scientific feasibility, methods, parameters, protocols, obligations,
  evaluation, or proposal content;
- enforce Data Explorer as the exclusive dataset-access boundary, Hypothesis
  Analyst as scientific owner without direct dataset access, and Graph Miner as
  read-only;
- implement the complete scientific investigation, Evidence request,
  protected evaluation, typed outcome, governance, and application admission
  lifecycle;
- bind Evidence to exact canonical lineage, require exactly one Hypothesis for
  each eligible feasible leaf scientific Task, and enforce at-most-one
  Discovery per Hypothesis;
- implement Objective-scoped validity propagation, context eligibility,
  SessionFrame governance, and restart-safe reconstruction;
- retain hard cutover, structural-only canonicalization, and fail-closed
  behavior with no semantic legacy fallback.

## Deferred implementation

These capabilities are intentionally not current support:

- executable DVC identity resolution and governed derived-dataset workflows;
- a result inbox, replay-safe specialist completion, and complete recovery
  orchestration;
- deployment adapters, authenticated service surfaces, and external tool
  integration;
- broader database verification and a migration strategy beyond the narrow
  SQLite execution-attempt upgrade;
- cache services whose keys include all validity and provenance inputs;
- user-facing interfaces. A product CLI remains outside the current phase.

Deferred work must still conform to the frozen authority and validity model.

## Exploratory improvements

These directions may be investigated but are not approved architecture:

- alternative relational or graph-backed physical storage while retaining the
  same application-authority admission contracts;
- hybrid lexical/vector ranking after exact eligibility filtering;
- performance-oriented projections or materialized views that remain
  non-authoritative and invalidation-aware;
- richer GeneratedView formats and user interfaces derived only from eligible
  admitted state.

## Unresolved but non-blocking considerations

- Exact serialization shapes and versioning for role-native specialist
  contracts remain to be fixed without changing their authority boundaries.
- The long-term physical split between relational persistence, semantic graph
  projection, provenance storage, and cache remains an implementation choice.
- Production scale targets, latency budgets, and retention policies have not
  been established.
- Any future CLI proposal must be separately approved; the current-phase
  decision is no supported product CLI.
