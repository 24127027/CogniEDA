# Agent Responsibility Boundaries

> **Authority:** canonical target responsibility contract.
> **Current implementation:** materially deviates from this target; see
> [Implementation Gap Analysis](implementation-gap-analysis.md). Audit reports are local-only verification artifacts under `.local/audits/`.

CogniEDA separates governance, scientific judgment, data execution, and governed retrieval.
PydanticAI owns every LLM-backed implementation of these roles. LangGraph may coordinate their
deterministic sequence, but it does not redefine their typed contracts or scientific authority.

## Planner

**Purpose.** Govern the investigation and present proposals and results to the user.

- **Allowed inputs:** latest user request, typed Planning/Answer Context, specialist proposals,
  approval records, workflow state, and commit results.
- **Typed output:** user response, clarification or approval request, ordered
  `PlannerOperation` proposals, specialist dispatch request, or controlled failure.
- **Permitted tools:** governed graph/context retrieval through Graph Miner, repository-backed
  workflow queries, approval services, specialist dispatch, and commit.
- **Forbidden operations:** raw-data analysis; selecting a scientific conclusion from numerical
  output; creating Evidence; using Assumptions as inference premises; silently changing an
  approved Hypothesis; direct arbitrary FCO writes; replacing Graph Miner traversal.
- **Persistence rights:** no direct FCO mutation. It may persist pending approval/workflow records
  and submit approved ordered operations to commit.
- **Failure contract:** return a typed, user-visible clarification, stale-proposal, unavailable-
  capability, authorization, or commit failure without partial research-state mutation.
- **Retry ownership:** retry transient Planner model calls within the PydanticAI boundary;
  re-plan stale workflow proposals instead of replaying them.
- **User-approval boundary:** required for research-direction, Task, Hypothesis, data-cleaning,
  execution-contract, Objective, Assumption, and conflict decisions according to governance mode.
  Scientific execution never starts before the exact Hypothesis contract is durably approved.
- **Idempotency:** proposal and resume tokens bind to one session, ordered operation set, and
  snapshot. Replaying a consumed proposal must not repeat mutations.
- **Provenance:** record request, selected context and inclusion reasons, specialist identity,
  proposal fingerprint, user decision, and resulting operation IDs.
- **Unit-test contract:** routing, context-role restrictions, operation production, approval
  binding, stale proposal rejection, and absence of scientific-object construction.
- **Integration-test contract:** request through approval and atomic commit, plus specialist
  handoff and resume after process replacement.

## Hypothesis Analyst

**Purpose.** Own the scientific test contract and evidence-bound evaluation in two explicit modes.

- **Allowed inputs — operationalization:** one active terminal analytical Task; accepted
  DataProfile metadata; Planning Context; relevant prior Discoveries; planning-only Assumptions;
  and user constraints.
- **Typed output — operationalization:** `HypothesisProposal` containing atomic claim, variable
  bindings, population/scope, derived metrics, claim type, method family or constraints, evidence
  expectation, decision rule, uncertainty requirements, validity threats, and required
  AnalysisFrame characteristics.
- **Allowed inputs — evidence evaluation:** approved Hypothesis, accepted DataProfile reference,
  AnalysisFrame provenance, admitted Evidence bundle, method/parameters, decision rule,
  uncertainty, and execution limitations. Assumptions and existing Discoveries are excluded.
- **Typed output — evidence evaluation:** `DiscoveryProposal` containing epistemic status,
  structured claim, strength, uncertainty, scope, validity envelope, supporting Evidence IDs, and
  explicit insufficient/inconclusive wording when applicable.
- **Permitted tools:** governed metadata/method catalogs and deterministic calculators that do not
  inspect or mutate raw datasets.
- **Forbidden operations:** dataframe execution, dataset mutation, Evidence production, graph or
  Task mutation, Assumptions as inference premises, unqualified fail-to-reject claims, and scope
  expansion beyond the approved Hypothesis.
- **Persistence rights:** none. Planner converts accepted proposals into operations; commit owns
  writes.
- **Failure contract:** typed `needs_clarification`, `contract_not_identifiable`,
  `evidence_inadmissible`, `insufficient_evidence`, or `scope_mismatch`, with no Discovery proposal
  when lineage is invalid.
- **Retry ownership:** PydanticAI retries model/structured-output failures. Domain-inadmissible
  inputs return a controlled failure and are not retried as model noise.
- **User-approval boundary:** the operationalized Hypothesis and decision rule require approval
  before dispatch. Evidence evaluation does not silently change that contract.
- **Idempotency:** identical typed input and model/method version should yield the same proposal
  identity; persistence cardinality is enforced separately.
- **Provenance:** prompt/context version, model identity, accepted input IDs, method constraints,
  decision rule, excluded context roles, and validation findings.
- **Unit-test contract:** both modes, Assumption exclusion in evaluation, scope preservation,
  fail-to-reject wording, and malformed lineage rejection.
- **Integration-test contract:** terminal Task to approved Hypothesis, and Evidence bundle to one
  commit-admissible Discovery proposal.

## Data Explorer

**Purpose.** Own data-facing inspection, profiling, approved cleaning, exploratory computation,
and execution of approved analytical contracts, returning observations rather than conclusions.

- **Allowed inputs:** a typed mode-specific request; governed dataset-version locator; current
  DataProfile metadata; approved cleaning decision when cleaning; or durable
  Task/Hypothesis/DataProfile/ExecutionRun identities, immutable execution specification,
  approved variable bindings and filters, artifact destination, environment, and seed when
  executing analysis.
- **Typed output:** a mode-specific profile/inspection result, a derived-dataset and new
  DataProfile proposal after approved cleaning, or observation-only `DataExplorerResult`
  containing AnalysisFrame and Evidence observations, method/provenance facts, sample and
  exclusion details, limitations, bounded diagnostics, or typed technical failure. Durable
  ExecutionRun completion remains application-owned and is not returned in the specialist payload.
- **Permitted tools:** dataset loaders, dataframe/statistical libraries, filesystem artifact store,
  and DVC/version resolver within the approved contract.
- **Forbidden operations:** changing the question, Hypothesis, scope, method family, or decision
  rule; producing Discovery; treating Assumptions as evidence; mutating FCOs; hiding exclusions or
  sample size.
- **Persistence rights:** no direct research-object writes. Application services own attempt
  transitions and receipt; Planner/commit own research-state persistence.
- **Failure contract:** preserve valid attempt provenance and technical diagnostics; do not attach
  Evidence to failed or contract-incompatible execution.
- **Retry ownership:** application worker owns lease, fencing, and technical-attempt retry. The Data
  Explorer does not create a new scientific contract during retry.
- **User-approval boundary:** cleaning and contract changes require a new proposal and approval.
  Technical implementation choices are allowed only inside the approved method constraints.
- **Idempotency:** honor execution-run ID, dispatch idempotency key, lease epoch, code/environment
  identity, and deterministic seed.
- **Provenance:** the application envelope binds exact dataset/DataProfile and attempt identity;
  Data Explorer reports frame hash/filter/columns, code and environment, parameters, seed,
  artifacts, exclusions, missing-data policy, sample size, and limitations without mirroring the
  envelope identifiers.
- **Unit-test contract:** contract adherence, deterministic execution, provenance completeness,
  failure isolation, and no Discovery output.
- **Integration-test contract:** durable outbox through fenced inbox with Evidence-ready observations
  and no direct FCO mutation.

## Graph Miner

**Purpose.** Retrieve and analyze governed project state, not raw data.

- **Allowed inputs:** typed retrieval request, Objective/Task/DataProfile/Evidence/Discovery graph
  relations, lifecycle metadata, SessionFrame selection policy, and context budget.
- **Typed output:** ranked `ContextBundle`, graph observations, coverage/orphan/staleness/conflict
  candidates, lineage paths, and proposed links/flags with inclusion reasons.
- **Permitted tools:** graph/repository traversal, lifecycle-aware retrieval, semantic ranking, and
  lineage validation.
- **Forbidden operations:** raw-dataset analysis, Evidence or scientific conclusion production,
  direct graph mutation, autonomous conflict resolution, similarity-as-proof, and promotion of
  generated summaries to Discovery.
- **Persistence rights:** none. It proposes graph operations; Planner and commit govern writes.
- **Failure contract:** typed partial/empty result with exclusions, unavailable relations, stale
  lineage, and truncation/budget diagnostics.
- **Retry ownership:** PydanticAI owns model-bound retries; repository/application code owns
  transient graph-query retries.
- **User-approval boundary:** none for read-only retrieval; proposed links, flags, pins, or removals
  follow Planner governance.
- **Idempotency:** identical graph snapshot, request, policy, scorer, and budget produce a stable
  ranked result.
- **Provenance:** snapshot/version, traversed relation types, filters, scorer/model version, scores,
  exclusions, context budget, and inclusion reasons.
- **Unit-test contract:** lifecycle/type filtering, lineage traversal, stale/orphan detection,
  deterministic ranking, and no mutation.
- **Integration-test contract:** typed context assembly for Planner and both specialist modes,
  including strict Discovery-synthesis exclusions.

## Responsibility Matrix

`A` is the single accountable owner. Supporting roles do not share accountability.

| Action | Accountable owner | Supporting boundary |
| --- | --- | --- |
| Create Task proposal | Planner | Graph Miner supplies governed context; user approves |
| Decompose Task | Planner | Graph Miner retrieves lineage; user approves |
| Compile Hypothesis | Hypothesis Analyst | Planner validates completeness and requests approval |
| Approve Hypothesis | User | Planner records and enforces the decision |
| Select scientific method/decision rule | Hypothesis Analyst | Data Explorer may choose implementation details within constraints |
| Execute analysis | Data Explorer | Application worker owns attempt protocol |
| Create AnalysisFrame proposal | Data Explorer | Commit persists accepted provenance |
| Create/complete ExecutionRun provenance | Application service | Data Explorer supplies bounded technical observations but no durable attempt identity or transition authority |
| Produce Evidence proposal | Data Explorer | Commit validates lineage and persists |
| Evaluate Evidence | Hypothesis Analyst | Deterministic domain validators check admissibility |
| Produce Discovery proposal | Hypothesis Analyst | Planner converts accepted proposal to operations |
| Detect conflict/staleness | Graph Miner | Planner presents review and proposes operations |
| Update SessionFrame proposal | Planner | Graph Miner supplies inclusion reasons |
| Create PlannerOperation | Planner | Specialist outputs are inputs, never direct writes |
| Commit persistent state | Commit/application service | Repositories enforce domain invariants atomically |

## Current Known Deviations

- Planner decomposition and `prepare_execution` author the analytical specification and
  `HypothesisDraft` (`src/agents/planner/types.py:357-483`,
  `src/agents/planner/nodes.py:971-1147`).
- The executor-facing and durable receipt boundary is the same observation-only
  `DataExplorerResult`; no compatibility evaluation bridge remains.
- Hypothesis Analyst evaluates a repository-built protected bundle and publishes only a proposal or
  failure. Atomic Discovery admission copies the exact approved proposal.
- Graph Miner remains outside the explicitly registered Data Explorer dispatcher, and a concrete
  Data Explorer adapter is not checked in.
