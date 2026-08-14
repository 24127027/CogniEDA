# CogniEDA Agent Guide

CogniEDA is validity-preserving research-state infrastructure for analytical
investigation. Do not treat it as generic chat memory, a notebook, or a vector
retrieval runtime.

Epistemic correctness is the highest priority: every claim must remain
traceable, scope-valid, and protected from the wrong state entering reasoning.

## Source of truth

- Source code and tests are authoritative for what currently exists.
- [docs/index.md](docs/index.md) links the canonical target owners.
- [docs/design-decisions/index.md](docs/design-decisions/index.md) records stable
  decisions and tradeoffs.
- [docs/status/current-state.md](docs/status/current-state.md) records the dated,
  evidence-qualified implementation boundary. Reverify source before changing
  a current claim.
- If target documentation and code differ, report the difference. Do not
  silently reinterpret either one.
- Verify the active branch and ancestry. Do not infer current branch topology
  from docs, reports, or prior work.

## Current implementation warning

All eight FCO names have schemas and SQLModel records. `PlannerOperation`,
`AnalysisFrame`, `ExecutionRun`, and other provenance/operational records also
exist. This does not establish the canonical workflow. Active Tasks have the
minimum Objective-scoped canonical semantic core, but only bounded `DATA` work
is executable. Immutable non-FCO Plan contracts, deterministic validation, and
append-only SQLite snapshot persistence exist, but Planner authoring, Human
approval, activation, active Plan selection, and scientific-investigation
contracts are absent;
Planner execution nodes and specialist graphs are stubs; DVC and product CLI
support are absent; database behavior is verified only on SQLite. Keep detailed
claims in the status track.

## Exact FCO and graph boundaries

The target FCO set is exactly:

- `Objective`
- `DataProfile`
- `Assumption`
- `Task`
- `Hypothesis`
- `Evidence`
- `Discovery`
- `SessionFrame`

The semantic Knowledge Graph contains exactly `Objective`, `Hypothesis`,
`Evidence`, and `Discovery`. `SessionFrame` is an FCO outside that graph.

Do not promote `Workspace`, `Question`, `Plan`, `AnalysisFrame`,
`GeneratedView`, `PlannerOperation`, `ExecutionRun`, `EvidenceCacheEntry`, or
other workflow/provenance/cache/presentation state into an FCO.

## Canonical Task and plan rules

- Task kinds are exactly `DATA`, `SCIENTIFIC`, and `GRAPH`.
- Planner response synthesis is Planner behavior, not a Task kind, capability,
  provider, or executor path. Not every user prompt becomes a Task.
- Do not add compatibility fallback from legacy `ANALYTICAL`, `ORGANIZING`, or
  `REVIEW` to canonical new-write paths.
- Task owns semantic work identity. Plan owns direct Task membership and
  structural dependency; workflow state outside Plan owns approval and
  activation. Independent Tasks are intentionally unordered.
- Semantic Task change creates a successor; coordination-only change creates a
  successor Plan without changing Task identity.
- Proposed Tasks cannot execute.
- Only an eligible feasible leaf `SCIENTIFIC` Task may enter scientific
  investigation and produce at most one Hypothesis.
- A parent Task produces neither a Hypothesis nor a Discovery.
- One Hypothesis produces at most one Discovery.

## Authority boundaries

- Human interaction is through Planner only.
- Planner coordinates Objective and plan work, consultations, approvals,
  routing, replanning, active context, and presentation. Planner does not
  author scientific feasibility, Hypotheses, methods, parameters, decision
  rules, protocols, Evidence obligations, protected evaluation, or
  DiscoveryProposal content.
- Data Explorer exclusively accesses datasets and performs bounded data work.
  It returns observations and provenance material; it does not evaluate.
- Hypothesis Analyst owns scientific feasibility, operationalization,
  protocols, obligations, and protected evaluation. It never accesses datasets
  directly.
- Graph Miner is read-only. It cannot mutate state, access datasets, perform
  governance, or create Evidence or Discovery.
- Governance may approve, reject, hold, or request correction, more Evidence,
  or conflict review. It does not rewrite scientific content or persist state.
- Application authority owns identity, validation, admission, persistence,
  atomic transitions, validity propagation, replay safety, and fail-closed
  enforcement.

## Epistemic and context discipline

- Keep intent, workflow, data state, Assumptions, scientific contracts,
  observations, claims, active context, provenance, and cache separate.
- Assumptions guide planning only and cannot be inference premises.
- Evidence is an admitted observation, not raw executor output or
  interpretation.
- Discovery is an evidence-bound admitted claim, not a summary or generated
  view.
- Conclusion and Discovery Synthesis Context exclude Assumptions, prior
  Discoveries, Tasks, raw chat, failed reasoning, invalid state, unverified
  views, and caches.
- Eligibility precedes relevance. Similarity never grants authority.
- Cross-Objective access and reuse fail closed unless an exact canonical
  admission contract authorizes them.
- Fail-to-reject and inconclusive outcomes must be phrased without claiming a
  stronger absence of relationship. Prefer: “available evidence is
  insufficient to reject independence within scope S using method M on
  DataProfile V.”

## Mutation, validity, and hard cutover

- DataProfile and Evidence payloads are immutable. Changed data creates a new
  dataset version and DataProfile; changed analytical output creates new
  Evidence with a traceable lifecycle relation.
- Evidence invalidation or supersession changes current-use eligibility without
  deleting historical truth.
- Discovery-to-Assumption contradiction creates a review signal and does not
  rewrite or delete the Assumption.
- Canonical new writes accept only canonical contracts. Legacy shapes may
  remain historical provenance but never fallback authority.
- Canonicalization is structural only; do not infer synonyms, units, semantic
  equivalence, cross-Objective compatibility, or missing scientific meaning.
- Missing identity, lineage, scope, authorization, or contract version fails
  closed.
- A supported product CLI is outside the current phase. Do not present the
  placeholder entry point or internal DB initializer as one.

## Planner pipeline target

Preserve this target pipeline unless an authoritative decision changes it:

```text
understand_request
route_intent
answer_question
propose_questions
expand_plan
manage_tasks
select_task
prepare_execution
dispatch_executor
review_execution
review_conflicts
manage_objective
manage_assumptions
request_user_input
pause
process_decision
commit
```

Planner nodes produce operations; commit atomically persists only approved
operations through application authority.

## Documentation rules

- Inspect code before editing documentation.
- Use only: `Implemented`, `Verified on SQLite`, `Partially implemented`,
  `Design target`, `Deferred`, `Known limitation`, and `Unsupported` for
  reader-facing implementation status.
- Name the boundary of every current claim. A file, schema, interface, stub,
  fixture, configuration key, or empty directory is not implementation proof.
- Update the status track when verified current behavior or limitations change.
- Do not turn a target, review report, owner decision, or generated summary into
  an implementation claim.
- Update README only with verified commands and supported boundaries.

## Implementation rules

- Classify a feature before implementation: FCO, workflow state, provenance,
  cache, filesystem artifact, or generated view.
- Default uncertain durable state to provenance or generated view, not durable
  scientific knowledge.
- Prefer explicit schemas, validators, lifecycle guards, and tests.
- Make the smallest coherent change that preserves the canonical model.
- Add or update tests for every invariant touched.

After a task, report what changed, the protected invariant, exact checks run,
and unresolved architectural risk.
