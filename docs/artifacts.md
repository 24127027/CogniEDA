# Artifact Contracts

## Cross-Cutting Contracts

- IDs are stable and explicit.
- Every artifact is attributable to one `Project`.
- Time or version fields are mandatory for reproducibility.
- Relationships use explicit references, not free-text inference.
- Status fields use controlled vocabularies, not ad hoc strings.
- Corrections create superseding artifacts or explicit status transitions, not silent overwrites.

## Current Storage Split

- The local SQLModel store is the runtime persistence surface for all first-class artifacts.
- `artifacts/dataset_assets/` and `artifacts/data_profiles/` are Git-tracked metadata mirrors and examples for reviewable dataset lineage and profile snapshots.
- Other first-class artifacts currently persist operationally through the local database scaffold, not as Git-tracked JSON files by default.

## Context-Memory Contract

- `SessionFrame` is the current persisted implementation of CogniEDA's broader `Context Frame` concept.
- Memory items carried inside a `SessionFrame` may record:
  - `memory_status`
  - `provenance`
  - `invalidation_rules`
  - `fresh_until`
- Stale, overruled, superseded, archived, and dead-end context should remain historically visible without continuing to influence active reasoning silently.
- Cached tool results, branch labels, checkpoint labels, and handoff summaries are first-class context data, not implicit chat residue.

## `Project`

**Purpose**

Root analytical container for objective, research questions, active scope, and durable defaults.

**Minimum required fields**

- `project_id`
- `name`
- `objective`
- `research_questions`
- `status`
- `created_at`
- `updated_at`

**Lifecycle / status notes**

- Expected top-level statuses: `active`, `paused`, `archived`.
- A project remains the parent context for all downstream artifacts even when paused.
- Archival preserves history; it does not delete analytical lineage.

**Relationships**

- Owns `DatasetAsset` records.
- Owns `Hypothesis` records.
- Owns `DecisionLog` records.
- Owns `SessionFrame` snapshots.
- Provides the parent scope for `Assumption`, `Evidence`, and `DataProfile` references.

## `DatasetAsset`

**Purpose**

Versioned reference to a raw or derived dataset used in analysis.

**Minimum required fields**

- `dataset_id`
- `project_id`
- `name`
- `source_type`
- `location`
- `version`
- `kind`
- `role`
- `upstream_dataset_ids`
- `lineage_steps`
- `created_at`
- `updated_at`

**Lifecycle / status notes**

- Raw versus derived role must be explicit.
- Raw assets are immutable references.
- Derived assets must preserve lineage to every upstream dataset they depend on.
- Transformations such as filters, joins, imputations, sampling, renames, feature engineering, and column drops should be recorded explicitly in `lineage_steps`.
- Replacing a dataset version creates a new asset version, not a silent overwrite.

**Relationships**

- Belongs to one `Project`.
- Can be the subject of one or more `DataProfile` snapshots.
- Can be referenced by `Evidence`.
- Can reference one or more upstream `DatasetAsset` records for lineage.

## `DataProfile`

**Purpose**

Reproducible structural and quality summary for a specific dataset version.

**Minimum required fields**

- `profile_id`
- `project_id`
- `dataset_id`
- `method`
- `schema_summary`
- `baseline_summary`
- `row_count`
- `column_count`
- `quality_flags`
- `created_at`

**Lifecycle / status notes**

- A profile is a snapshot tied to one dataset version and one profiling method.
- Profiles are append-first records, not mutable rolling summaries.
- A new profile should be created when the dataset version or profiling method changes materially.

**Relationships**

- Belongs to one `DatasetAsset`.
- Informs `Assumption` generation.
- Supports preprocessing and validation planning.
- Can be cited by `Evidence` and `DecisionLog` rationale.

## `Assumption`

**Purpose**

Provisional statement used to guide analysis.

**Minimum required fields**

- `assumption_id`
- `project_id`
- `statement`
- `basis`
- `confidence`
- `status`
- `created_at`
- `updated_at`

**Key optional relational fields**

- `dataset_id`
- `profile_id`

**Lifecycle / status notes**

- Controlled statuses: `active`, `validated`, `rejected`, `archived`.
- Assumptions begin as provisional and should not be promoted to fact without evidence.
- A rejected assumption remains historically useful and should not be deleted silently.

**Relationships**

- Belongs to one `Project`.
- Often derives from `DataProfile` observations or prior `Evidence`.
- Can support one or more `Hypothesis` records.
- Can be linked directly from `Evidence`.

## `Hypothesis`

**Purpose**

Testable analytical claim.

**Minimum required fields**

- `hypothesis_id`
- `project_id`
- `statement`
- `variables`
- `scope`
- `validation_method`
- `status`
- `assumption_ids`
- `dataset_ids`
- `created_at`
- `updated_at`

**Lifecycle / status notes**

- Controlled statuses: `proposed`, `planned`, `validating`, `supported`, `refuted`, `inconclusive`, `archived`.
- Status changes must reflect explicit analytical progress.
- A supported or refuted status requires linked evidence.
- An inconclusive hypothesis remains active history and may branch into refined hypotheses later.

**Relationships**

- Belongs to one `Project`.
- May depend on one or more `Assumption` records.
- Is evaluated by one or more `Evidence` records.
- May motivate `DecisionLog` entries.

## `Evidence`

**Purpose**

Reproducible result from a concrete method run.

**Minimum required fields**

- `evidence_id`
- `project_id`
- `dataset_id`
- `evidence_type`
- `method`
- `parameters`
- `provenance`
- `result_summary`
- `limitations`
- `assumption_ids`
- `hypothesis_evaluations`
- `decision_ids`
- `created_at`

**Lifecycle / status notes**

- Evidence is immutable once captured.
- Corrections or reruns should create new evidence that supersedes earlier evidence where appropriate.
- Evidence may support, refute, or leave a hypothesis inconclusive through typed `hypothesis_evaluations`.
- `dataset_id` is the authoritative link to the versioned dataset asset; provenance should not duplicate version labels independently.

**Relationships**

- Belongs to one `Project`.
- References one `DatasetAsset`.
- Can link to `Assumption` records.
- Can link to `Hypothesis` records with an explicit typed outcome per hypothesis.
- Can support `DecisionLog` entries.
- May reference output files, plots, or reports produced by the method run.

## `DecisionLog`

**Purpose**

Record of meaningful analytical choices.

**Minimum required fields**

- `decision_id`
- `project_id`
- `decision_type`
- `decision`
- `rationale`
- `status`
- `alternatives_considered`
- `assumption_ids`
- `hypothesis_ids`
- `created_at`
- `updated_at`

**Key optional relational fields**

- `superseded_by_decision_id`

**Lifecycle / status notes**

- Controlled statuses: `active`, `superseded`, `rejected`, `archived`.
- Supersession must be explicit rather than implied by newer notes.
- Decisions record analytical governance, not just final outcomes.

**Relationships**

- Belongs to one `Project`.
- References supporting `Evidence` indirectly through evidence-to-decision links, with `Evidence` as the source of truth for that relation.
- May cite related `Hypothesis` and `Assumption` records.
- Affects future analysis plans and interpretation boundaries.

## `SessionFrame`

**Purpose**

Concrete persisted context frame for continuity, checkpointing, branching, and handoff across sessions or agents.

**Minimum required fields**

- `session_frame_id`
- `project_id`
- `frame_topic`
- `frame_status`
- `objective_snapshot`
- `dataset_summaries`
- `active_dataset_refs`
- `active_assumptions`
- `active_assumption_refs`
- `active_hypotheses`
- `active_hypothesis_refs`
- `strongest_evidence`
- `strongest_evidence_refs`
- `recent_decisions`
- `recent_decision_refs`
- `pending_tasks`
- `open_questions`
- `key_warnings`
- `stale_context`
- `dead_ends`
- `cached_tool_results`
- `frame_invalidation_rules`
- `created_at`

**Key optional frame-governance fields**

- `frame_outcome`
- `project_summary`
- `branch_key`
- `checkpoint_label`
- `parent_session_frame_id`
- `handoff_summary`

**Lifecycle / status notes**

- Session frames are append-only snapshots.
- `SessionFrame` is the current concrete artifact that carries the generalized `Context Frame` semantics described for CogniEDA.
- Later frames supersede earlier frames operationally, but earlier frames remain historical records.
- Stale context, dead ends, and cached tool results should be recorded explicitly rather than left implicit in conversation history.
- A session frame summarizes active state; it does not replace underlying artifacts.

**Relationships**

- Belongs to one `Project`.
- Summarizes current references to `DatasetAsset`, `Assumption`, `Hypothesis`, `Evidence`, and `DecisionLog`.
- May point to a parent frame for checkpoint or branch continuity.
- May carry cached tool results and invalidation rules for reuse in later agent work.
