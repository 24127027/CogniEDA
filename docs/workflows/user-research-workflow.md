# User Research Workflow

## Implementation Status

Partially implemented scaffold.

The repo has target FCO schemas, repositories, profiling utilities, session-frame construction, and planner/executor contract stubs. It does not implement an end-to-end user workflow.

## Target Workflow

### 1. Initialize Workspace And Objective

Target design:

- User opens or creates a filesystem workspace.
- Workspace is a runtime/filesystem boundary, not an FCO.
- Each workspace owns one independent graph database.
- User creates the first `Objective` FCO.
- Objective refinements preserve prior versions as provenance.

Current implementation:

- `Objective` schema/table/repository exist.
- Default persistence is workspace-local SQLite.
- No workspace initializer or registry exists.
- No `ObjectiveRevision` provenance exists.

Status: Partially implemented.

### 2. Mount Dataset And Generate DataProfile

Target design:

- User mounts a dataset into the workspace.
- The system creates an immutable `DataProfile` for the dataset version.
- `DataProfile` records dataset path, DVC/version identity, schema, row/column counts, missingness, descriptive statistics, artifacts, and preprocessing history.

Current implementation:

- `DatasetProfiler` can profile a pandas dataframe or loaded file into a `DataProfile`.
- `DataProfile` stores dataset path, optional DVC identity, source metadata, summaries, preprocessing history, lifecycle, and acceptance fields.
- Executable DVC integration is not implemented; the adapter boundary raises explicit not-implemented behavior.

Status: Partially implemented.

### 3. Cleaning Loop

Target design:

- User reviews the latest `DataProfile`.
- Planner proposes cleaning options.
- User decides; the agent does not silently choose.
- Cleaning creates a new dataset version and a new immutable `DataProfile`.
- User repeats until an accepted `DataProfile` becomes ground truth for later analysis.

Current implementation:

- `DataProfile` and `LineageStep` can represent preprocessing history.
- No cleaning execution service, user-decision loop, or cleaning provenance ledger exists.

Status: Partially implemented.

### 4. Assumption Admission

Target design:

- User may add `Assumption` objects after data review.
- Planner checks whether each statement is a framing axiom or a testable claim.
- Testable claims should be rejected as assumptions and proposed as Tasks/Hypotheses instead.
- Assumptions can guide planning but cannot enter Conclusion/Discovery Synthesis Context.

Current implementation:

- `Assumption` schema/table/repository exist.
- `Assumption` stores source, testability, scope, scoped DataProfile ids, contradiction Discovery refs, and replacement refs.
- Schema admission rejects claims marked as testable so they can be converted into Task/Hypothesis candidates instead of Assumptions.
- `SessionContextBuilder` excludes assumptions from conclusion/discovery-synthesis context.
- No planner warning flow or complete Objective-bound retrieval strategy
  exists. Current local policy covers only a subset of context modes and
  lifecycle/type checks.

Status: Partially implemented.

### 5. Task Proposal And Decomposition

Target design:

- Planner proposes task operations before durable Task creation.
- Approved Tasks become active.
- Broad work is decomposed into leaf Tasks of canonical kind `DATA`,
  `SCIENTIFIC`, `GRAPH`, or `SYNTHESIS` as required by the deliverables.

Current implementation:

- `Task` schema/table/repository exist with proposed/active/paused/completed/failed/rejected/cancelled lifecycle.
- Proposed Tasks can appear in planning SessionFrame context but cannot generate Hypotheses.
- `HypothesisRepository.create()` rejects Hypothesis creation from non-active, non-analytical, parent, unaccepted-DataProfile, or duplicate Task sources.
- Planner task-management nodes are stubs.

Status: Partially implemented.

### 6. SessionFrame Governance

Target design:

- `SessionFrame` is a governed active-context FCO outside the semantic
  Knowledge Graph.
- It is bound to an Objective, purpose, reasoning mode, scope, lifecycle point,
  and validity basis.
- It selects bounded references without transferring authority or replacing a
  protected EvaluationBundle.

Current implementation:

- `SessionFrame` snapshots store compact profile, task, assumption, hypothesis, discovery, evidence, decision-provenance, stale-context, dead-end, cache, and warning summaries.
- Planning, answer, and discovery-synthesis projection is implemented locally.
- Existing Discoveries are available for planning and answer context but excluded from discovery-synthesis context.
- Current frames are not explicitly bound by Objective identifier, purpose,
  reasoning mode, or the complete target eligibility record.

Status: Partially implemented.

The canonical owner is [SessionFrame](../concepts/context/session-frame.md).

### 7. Execution, Evidence, And Discovery

Target design:

- Only an eligible feasible leaf `SCIENTIFIC` Task can source at most one
  `Hypothesis`; a parent Task sources none.
- Hypothesis Analyst owns feasibility and scientific operationalization;
  Planner does not author the Hypothesis or protocol.
- Admitted EvidenceRequests are executed through Data Explorer under derived
  DataWorkOrders and exact ExecutionRun/AnalysisFrame provenance.
- Application authority, not an executor, admits immutable `Evidence`.
- Protected evaluation may create a `DiscoveryProposal` or typed
  non-completion.
- Governance authorizes an exact proposal without rewriting it; application
  authority atomically admits at most one Discovery for the Hypothesis.

The [Scientific lifecycle](../concepts/scientific-lifecycle/index.md) owns this
sequence and its contracts.

Current implementation:

- `Hypothesis`, `Evidence`, and `Discovery` schemas/tables/repositories exist.
- Evidence requires `DataProfile`, `AnalysisFrame`, and `ExecutionRun` references.
- Discovery requires Evidence and `validity_basis`.
- Repository guards enforce legacy upper bounds for one Task to one Hypothesis
  and one Hypothesis to one Discovery for fresh local stores.
- Generic executor contracts predate the canonical role-native contracts.
- Executor nodes are stubs.

Status: Partially implemented.

### 8. Conflict Review

Target design:

- New Discovery may be compared with Assumptions and existing knowledge.
- Contradictions flag objects for user review.
- The system must not automatically rewrite or delete Assumptions.

Current implementation:

- `Discovery` exists.
- `AssumptionRepository.flag_for_contradiction()` can mark an Assumption `flagged` and record the contradicting Discovery id without rewriting the Assumption.
- No automatic conflict-review planner implementation was found.

Status: Partially implemented.

### 9. Workspace Closure

Target design:

- User reviews open Tasks, testing Hypotheses, and flagged Assumptions.
- Planner traverses Objective, Tasks, Hypotheses, Evidence, Discoveries, Assumptions, DataProfiles, and provenance records to generate a research summary.
- Summary output is a GeneratedView. A new claim must follow the complete
  [scientific lifecycle](../concepts/scientific-lifecycle/index.md), including
  protected evaluation, governance, and application-authority admission.

Current implementation:

- No closure workflow or target summary generation exists.

Status: Design target.
