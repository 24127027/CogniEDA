# Task To Discovery Lifecycle

## Target Design

The target lifecycle is:

```text
Objective
  -> Task proposal and approval
  -> active terminal analytical Task
  -> exactly one Hypothesis
  -> execution over DataProfile and AnalysisFrame
  -> immutable Evidence
  -> exactly one Discovery
```

## Target Invariants

- Proposed Tasks cannot execute.
- Only active terminal analytical Tasks can generate Hypotheses.
- A terminal analytical Task must have no children.
- A terminal analytical Task must use an accepted DataProfile.
- A terminal analytical Task must contain one evaluable claim.
- A terminal analytical Task must have grounded variables or derivable metrics.
- A terminal analytical Task must define evidence expectation.
- One terminal analytical Task generates exactly one Hypothesis.
- One Hypothesis produces exactly one Discovery.
- Parent Tasks do not produce Discoveries.
- Parent-task answers are `GeneratedView`s over descendant Discoveries, Evidence, and provenance.

## Current Implementation

Current implementation:

- `Objective`, `Task`, `Hypothesis`, `Evidence`, `Discovery`, and `SessionFrame` schemas, SQLModel tables, and repositories exist.
- `TaskLifecycleState` includes `proposed`, `active`, `paused`, `completed`, `failed`, `rejected`, and `cancelled`.
- `Task.can_generate_hypothesis()` rejects proposed, rejected, paused, failed, cancelled, non-analytical, unscoped, and under-specified Tasks.
- `HypothesisRepository.create()` rejects Hypotheses unless the source Task exists, is active, analytical, has no child Tasks, uses an active accepted DataProfile, matches the Hypothesis profile, and has no existing Hypothesis.
- The database schema adds a unique constraint for one Task to one Hypothesis in fresh databases.
- `DiscoveryRepository.create()` rejects Discoveries unless the Hypothesis exists, all Evidence exists, all Evidence is active, all Evidence belongs to the same Hypothesis, and the Hypothesis has no existing Discovery.
- The database schema adds a unique constraint for one Hypothesis to one Discovery in fresh databases.
- `GeneratedView` does not exist.
- `Evidence` exists as an immutable schema/table/repository and requires `analysis_frame_ref` and `execution_run_ref`.
- Minimal durable `AnalysisFrame` and execution-attempt `ExecutionRun` records are persisted; they do not yet provide a full reproducibility envelope.
- Planner task selection, execution preparation, durable approval and execution admission are implemented. Dispatch, result receipt and scientific finalization run independently under `application/orchestrator`, not as planner graph nodes.

## Implementation Status

Partially implemented local schema and repository enforcement.

## Current Partial Support

Current `Task`, `Hypothesis`, `Evidence`, and `Discovery` repositories support:

- proposed/active/paused/completed/failed/rejected/cancelled Task lifecycle persistence
- terminal analytical Task admission checks before Hypothesis creation
- one Task to one Hypothesis guard at repository and fresh-database schema level
- hypothesis creation and lifecycle/status updates
- hypothesis listing by task/profile/status
- evidence creation and retrieval by hypothesis/profile
- evidence supersession/invalidation helpers with optional same-session dependent-Discovery review flagging
- typed evidence-to-hypothesis evaluation outcomes
- Discovery creation and retrieval by Hypothesis/status/review state
- repository-level Discovery review flagging after referenced Evidence changes
- one Hypothesis to one Discovery guard at repository and fresh-database schema level

This enforcement is exercised by one narrow approved deterministic-test path from execution admission through scientific finalization. It is not a general end-to-end analytical product because default executors, natural-language planning, general approvals and service/worker bootstrap remain incomplete.

## Architectural Risk

The main remaining lifecycle risk is not local repository admission; it is orchestration consistency. Retry currently attempts to clone a Hypothesis for the same Task and fails, approval is currently implemented only for Task-operation batches and execution contracts, an orphan outbox operation can be marked committed without a row, and supersession propagation is not atomic across dependent records.
