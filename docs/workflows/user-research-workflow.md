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
- Assumptions can guide planning but cannot enter Conclusion Context.

Current implementation:

- `Assumption` schema/table/repository exist.
- `SessionContextBuilder` excludes assumptions from conclusion context.
- No testability admission check or graph retrieval policy exists.

Status: Partially implemented.

### 5. Task Proposal And Decomposition

Target design:

- Planner proposes task operations before durable Task creation.
- Approved Tasks become active.
- Broad Tasks are decomposed into child Tasks until terminal analytical Tasks are reached.

Current implementation:

- `Task` schema/table/repository exist with active/paused/completed/failed/cancelled lifecycle.
- Durable proposed/rejected Task states are not used.
- Planner task-management nodes are stubs.

Status: Partially implemented.

### 6. SessionFrame Governance

Target design:

- `SessionFrame` is visible active context.
- User can inspect, pin, remove, reorder, or exclude items.
- Every item has an inclusion reason and audit note.

Current implementation:

- `SessionFrame` snapshots store compact profile, task, assumption, hypothesis, discovery, evidence, decision-provenance, stale-context, dead-end, cache, and warning summaries.
- Planning vs conclusion projection is implemented locally.
- No UI or per-item user governance exists.

Status: Partially implemented.

### 7. Execution, Evidence, And Discovery

Target design:

- A terminal analytical Task compiles into exactly one `Hypothesis`.
- Planner prepares execution and dispatches a specialist executor.
- Executor creates or references AnalysisFrame provenance.
- Executor produces immutable `Evidence`.
- Executor authors a `Discovery` draft as an evidence-bound claim.
- Commit persists approved executor outputs with execution provenance.

Current implementation:

- `Hypothesis`, `Evidence`, and `Discovery` schemas/tables/repositories exist.
- Evidence requires `DataProfile`, `AnalysisFrame`, and `ExecutionRun` references.
- Discovery requires Evidence and `validity_basis`.
- Executor contracts can return Evidence/Discovery drafts.
- Executor nodes are stubs.

Status: Partially implemented.

### 8. Conflict Review

Target design:

- New Discovery may be compared with Assumptions and existing knowledge.
- Contradictions flag objects for user review.
- The system must not automatically rewrite or delete Assumptions.

Current implementation:

- `Discovery` exists.
- No conflict-review implementation was found.

Status: Mostly not implemented.

### 9. Workspace Closure

Target design:

- User reviews open Tasks, testing Hypotheses, and flagged Assumptions.
- Planner traverses Objective, Tasks, Hypotheses, Evidence, Discoveries, Assumptions, DataProfiles, and provenance records to generate a research summary.
- Summary output is a generated view unless new claims go through Task -> Hypothesis -> Evidence -> Discovery.

Current implementation:

- No closure workflow or target summary generation exists.

Status: Design target.
