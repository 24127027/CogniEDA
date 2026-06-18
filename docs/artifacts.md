# Artifact Contracts

## Cross-Cutting Contracts

- IDs are stable and explicit.
- Every artifact must be attributable to a `Project`.
- Time or version fields are mandatory for reproducibility.
- Relationships must be explicit references, not inferred from free text.
- Status fields use controlled vocabularies, not ad hoc strings.
- Corrections should create superseding artifacts or status transitions, not silent overwrites.

## `Project`

**Purpose**

Root analytical container for objective, research questions, active scope, and durable defaults.

**Minimum fields**

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

**Minimum fields**

- `dataset_id`
- `project_id`
- `name`
- `source_type`
- `location`
- `version`
- `role`
- `parent_dataset_id` optional
- `created_at`

**Lifecycle / status notes**

- Raw versus derived role must be explicit.
- Raw assets are immutable references.
- Derived assets must preserve lineage to their parent dataset or transformation source.
- Replacing a dataset version creates a new asset version, not a silent overwrite.

**Relationships**

- Belongs to one `Project`.
- Can be the subject of one or more `DataProfile` snapshots.
- Can be referenced by `Evidence`.
- Can reference another `DatasetAsset` through `parent_dataset_id` for lineage.

## `DataProfile`

**Purpose**

Reproducible structural and quality summary for a specific dataset version.

**Minimum fields**

- `profile_id`
- `dataset_id`
- `method`
- `created_at`
- `schema_summary`
- `row_count`
- `column_count`
- `quality_flags`

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

**Minimum fields**

- `assumption_id`
- `project_id`
- `statement`
- `basis`
- `confidence`
- `status`
- `created_at`

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

**Minimum fields**

- `hypothesis_id`
- `project_id`
- `statement`
- `variables`
- `scope`
- `validation_method`
- `status`
- `created_at`

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

**Minimum fields**

- `evidence_id`
- `project_id`
- `dataset_id`
- `method`
- `parameters`
- `result_summary`
- `limitations`
- `created_at`

**Lifecycle / status notes**

- Evidence is immutable once captured.
- Corrections or reruns should create new evidence that supersedes earlier evidence where appropriate.
- Evidence may support, refute, or leave a hypothesis inconclusive.

**Relationships**

- Belongs to one `Project`.
- References one `DatasetAsset`.
- Can link to `Assumption` records.
- Can link to `Hypothesis` records.
- Can support `DecisionLog` entries.
- May reference output files, plots, or reports produced by the method run.

## `DecisionLog`

**Purpose**

Record of meaningful analytical choices.

**Minimum fields**

- `decision_id`
- `project_id`
- `decision`
- `rationale`
- `status`
- `evidence_refs`
- `alternatives_considered`
- `created_at`

**Lifecycle / status notes**

- Controlled statuses: `active`, `superseded`, `rejected`, `archived`.
- Supersession must be explicit rather than implied by newer notes.
- Decisions record analytical governance, not just final outcomes.

**Relationships**

- Belongs to one `Project`.
- References supporting `Evidence`.
- May cite related `Hypothesis` and `Assumption` records.
- Affects future analysis plans and interpretation boundaries.

## `SessionFrame`

**Purpose**

Compact state handoff for continuity across sessions.

**Minimum fields**

- `session_frame_id`
- `project_id`
- `objective_snapshot`
- `active_dataset_refs`
- `active_assumption_refs`
- `active_hypothesis_refs`
- `pending_tasks`
- `created_at`

**Lifecycle / status notes**

- Session frames are append-only snapshots.
- Later frames supersede earlier frames operationally, but earlier frames remain historical records.
- A session frame summarizes active state; it does not replace underlying artifacts.

**Relationships**

- Belongs to one `Project`.
- Summarizes current references to `DatasetAsset`, `Assumption`, and `Hypothesis`.
- May reflect recent `DecisionLog` outcomes and strongest current `Evidence`.
