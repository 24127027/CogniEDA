# User Research Workflow

## Implementation Status

Partially implemented backend prototype.

The repo has FCO/provenance persistence, profiling, session-frame projection, an approval-gated execution admission path, a durable worker protocol, and one deterministic scientific-finalization path. It still does not implement an end-to-end user product workflow because natural-language planning, default executors, cleaning, retrieval, UI/API and worker bootstrap are incomplete.

## Target Workflow

### 1. Initialize Workspace And Objective

Target design:

- User opens or creates a filesystem workspace.
- Workspace is a runtime/filesystem boundary, not an FCO.
- Each workspace owns one independent graph database.
- User creates the first `Objective` FCO.
- Objective lifecycle changes preserve stable Objective identity and remain attributable to committed operations.

Current implementation:

- `Objective` schema/table/repository exist.
- Default persistence is workspace-local SQLite.
- No workspace initializer or registry exists.
- `/objective` resolves current and historical Objectives to graph-local references,
  produces a typed exact operation batch, and requires the matching session-bound
  fingerprint plus ordered operation IDs before commit.
- `Objective.status` is authoritative. At most one row may be `ACTIVE`; a partial
  SQLite unique index enforces this across concurrent writers. Completion and
  archival require explicit approval and are rejected while any proposed, active,
  or paused Task remains in the workspace.
- Governed updates atomically append an immutable non-FCO `ObjectiveRevision` and
  a successor `SessionFrame`. Direct import/repair bypasses are explicitly named.
- `PAUSED` remains a compatibility lifecycle state but is not the current Objective
  used by Step 5 or default planning/answer retrieval.

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
- No planner warning flow or graph retrieval engine exists. A pure type/lifecycle retrieval policy does exist under `src/memory/retrieval_policy.py`.

Status: Partially implemented.

### 5. Task Proposal And Decomposition

Target design:

- Planner proposes task operations before durable Task creation.
- Approved Tasks become active.
- Broad Tasks are decomposed into child Tasks until terminal analytical Tasks are reached.

Current implementation:

- `Task` schema/table/repository exist with proposed/active/paused/completed/failed/rejected/cancelled lifecycle.
- Proposed Tasks can appear in planning SessionFrame context but cannot generate Hypotheses.
- `HypothesisRepository.create()` rejects Hypothesis creation from non-active, non-analytical, parent, unaccepted-DataProfile, or duplicate Task sources.
- `manage_tasks` can turn already-supplied typed drafts into PlannerOperations, but the public planner path does not yet produce those drafts or complete general Task approval.

Status: Partially implemented.

### 6. SessionFrame Governance

Target design:

- `SessionFrame` is visible active context.
- User can inspect, pin, remove, reorder, or exclude items.
- Every item has an inclusion reason and audit note.

Current implementation:

- `SessionFrame` snapshots store compact profile, task, assumption, hypothesis, discovery, evidence, decision-provenance, stale-context, dead-end, cache, and warning summaries.
- Planning, answer, and discovery-synthesis projection is implemented locally.
- Existing Discoveries are available for planning and answer context but excluded from discovery-synthesis context.
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
- Repository guards enforce one Task to one Hypothesis and one Hypothesis to one Discovery for fresh local stores.
- Approved execution admission persists Hypothesis/ExecutionRun/outbox state. An independent worker persists an inbox result and a fenced finalizer can create AnalysisFrame/Evidence/Discovery/lifecycle/SessionFrame operations for one deterministic method.
- The durable worker now validates persisted attempt identity and reaches the capability registry through one `ExecutorInput` adapter. The canonical `ExecutorResult` observation schema exists, but default executor graph builders remain explicit stubs.

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
- Summary output is a generated view unless new claims go through Task -> Hypothesis -> Evidence -> Discovery.

Current implementation:

- No closure workflow or target summary generation exists.

Status: Design target.
