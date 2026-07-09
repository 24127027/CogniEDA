# First-Class Objects

## Target Design

A First-Class Object is admitted only when it needs explicit identity, lifecycle, user-control semantics, retrieval policy, and epistemic role.

The canonical FCO set is:

- `Objective`
- `DataProfile`
- `Assumption`
- `Task`
- `Hypothesis`
- `Evidence`
- `Discovery`
- `SessionFrame`

The design explicitly excludes `Workspace`, `Question`, `AnalysisFrame`, `GeneratedView`, `PlannerOperation`, `ExecutionRun`, and `EvidenceCacheEntry` from the FCO set.

## Current Implementation Status

| Concept | Status | Current implementation |
| --- | --- | --- |
| `Objective` | Implemented | Schema, SQLModel table, and repository exist for workspace-local research intent. |
| `DataProfile` | Implemented locally | Immutable schema, table, repository, and profiler exist. It stores dataset path, optional DVC identity, source metadata, summaries, preprocessing history, lifecycle state, replacement profile id when superseded, and ground-truth acceptance. |
| `Assumption` | Partially implemented | Schema, table, and repository exist. Assumptions are planning context only and are excluded from conclusion projection. |
| `Task` | Partially implemented | Schema, table, repository, lifecycle, and local hypothesis-readiness guard exist. Planner operation integration is still missing. |
| `Hypothesis` | Partially implemented | Schema, table, and repository exist. It references one Task and one DataProfile. Admission cardinality is not database-enforced. |
| `Evidence` | Implemented locally | Immutable schema, table, and append-only repository exist. It references Hypothesis, DataProfile, AnalysisFrame, and ExecutionRun. |
| `Discovery` | Implemented locally | Immutable schema, table, repository, structured claim, epistemic status, and `validity_basis` enforcement exist. |
| `SessionFrame` | Partially implemented | Schema, table, repository, builder, and planning/conclusion projection exist. Target user-governed context-item audit details remain incomplete. |

## Current Non-FCO Boundaries

| Concept | Status | Implementation note |
| --- | --- | --- |
| Workspace | Valid infrastructure | Represented by filesystem path and database URL, not by a research graph object. |
| AnalysisFrame | Valid provenance | Minimal non-FCO schema/table/repository exists; full analytical-view provenance is not implemented. |
| ExecutionRun | Valid provenance | Minimal non-FCO schema/table/repository exists; executor runtime provenance is not implemented. |
| PlannerOperation | Valid workflow/provenance | Minimal non-FCO schema/table/repository and skeleton commit boundary exist; approval/rollback machinery is not implemented. |
| UserDecision | Valid provenance | Typed provenance record, not an FCO. |
| Evidence cache | Not implemented | Must remain an optimization index and must not create Discovery. |

## Admission Rule

Future durable additions must first answer:

- Is this research intent, workflow state, data state, planning constraint, test contract, observed result, evidence-bound claim, or active context?
- Does it require its own lifecycle and user controls?
- Can it affect future reasoning, and in which context mode?
- Could it instead be provenance, cache, filesystem artifact, or generated view?

When uncertain, default to provenance or generated view rather than durable knowledge.
