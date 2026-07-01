# User Research Workflow

## Implementation Status

Design target.

The current repo does not implement an end-to-end user workflow. It has schemas, repositories, profiling utilities, session-frame construction, and planner graph stubs. The workflow below is the target workflow from the internal user-agent workflow design, adapted to the final FCO architecture.

## Target Workflow

### 1. Initialize Workspace And Objective

Target design:

- User opens or creates a filesystem workspace.
- Workspace is a runtime/filesystem boundary, not an FCO.
- User creates the first `Objective` FCO with title, description, guiding questions, and optional orientation.
- Objective refinements preserve prior versions as provenance rather than overwriting history.

Current implementation:

- No workspace initializer exists.
- No `Objective` model exists.
- Current `Project` stores `objective` and `research_questions`.

Status: Implementation deviates from target.

### 2. Mount Dataset And Generate DataProfile

Target design:

- User mounts a dataset into the workspace.
- The system creates an immutable `DataProfile` for the dataset version.
- `DataProfile` records dataset path, DVC/version identity, schema, row/column counts, missingness, descriptive statistics, anomalies, correlation summaries, profile artifacts, and preprocessing history.

Current implementation:

- `DatasetProfiler` can profile a pandas dataframe or loaded file into a current `DataProfile`.
- Current `DataProfile` stores schema summary, baseline summary, counts, quality flags, method, project ID, dataset ID, and creation time.
- DVC hash, acceptance as ground truth, anomaly/correlation summaries, and preprocessing history are not implemented in the target form.

Status: Partially implemented.

### 3. Cleaning Loop

Target design:

- User reviews the latest `DataProfile`.
- Planner proposes cleaning options.
- User decides; the agent does not silently choose.
- Cleaning creates a new dataset version and a new immutable `DataProfile`.
- User repeats until an accepted `DataProfile` becomes ground truth for later analysis.

Current implementation:

- `DatasetAsset` supports raw/derived roles and lineage steps.
- `DataProfileRepository` is append-only.
- No cleaning service, DVC integration, user-decision loop, accepted-ground-truth field, or cleaning provenance ledger exists.

Status: Partially implemented.

### 4. Assumption Admission

Target design:

- User may add `Assumption` objects after data review.
- Planner checks whether each statement is a framing axiom or a testable claim.
- Testable claims should be rejected as assumptions and proposed as Tasks/Hypotheses instead.
- Assumptions can guide planning but cannot enter Conclusion Context.

Current implementation:

- `Assumption` schema/table/repository exist.
- No testability admission check was found.
- No context-mode retrieval enforcement was found.

Status: Partially implemented.

### 5. Task Proposal And Decomposition

Target design:

- Planner proposes `Task` objects from Objective, DataProfile, Assumptions, and existing Discoveries.
- Proposed Tasks are shown for user approval.
- Approved Tasks become active.
- Broad Tasks are decomposed into child Tasks until terminal analytical Tasks are reached.

Current implementation:

- No `Task` model exists.
- Planner node names exist, but task management nodes are stubs.
- `SessionFrame.pending_tasks` stores strings only.

Status: Not implemented.

### 6. SessionFrame Governance

Target design:

- `SessionFrame` is visible active context.
- User can inspect, pin, remove, reorder, or exclude items.
- Every item has an inclusion reason and audit note.

Current implementation:

- Current `SessionFrame` snapshots can store compact summaries, stale context, dead ends, cached tool-result summaries, and invalidation rules.
- No UI or per-item user governance exists.

Status: Partially implemented.

### 7. Execution, Evidence, And Discovery

Target design:

- A terminal analytical Task compiles into exactly one `Hypothesis`.
- Planner prepares execution and dispatches a specialist executor.
- Executor creates or references `AnalysisFrame` provenance.
- Executor produces immutable `Evidence`.
- Planner reviews execution and creates exactly one `Discovery` for the `Hypothesis`.
- Discovery includes a `ValidityEnvelope`.

Current implementation:

- `Hypothesis` and `Evidence` exist in older/current forms.
- No `Task`, `AnalysisFrame`, `ExecutionRun`, `Discovery`, or `ValidityEnvelope` exists.
- Execution nodes are stubs.

Status: Mostly not implemented.

### 8. Conflict Review

Target design:

- New Discovery may be compared with Assumptions and existing knowledge.
- Contradictions flag objects for user review.
- The system must not automatically rewrite or delete Assumptions.

Current implementation:

- No Discovery object exists.
- No conflict review implementation was found.

Status: Not implemented.

### 9. Project Closure

Target design:

- User reviews open Tasks, testing Hypotheses, and flagged Assumptions.
- Planner traverses Objective, Tasks, Hypotheses, Evidence, Discoveries, Assumptions, DataProfiles, and provenance records to generate a research summary.
- User reviews and closes the project.

Current implementation:

- Current `Project` has `active`, `paused`, and `archived` statuses.
- No closure workflow or target summary generation exists.

Status: Design target.
