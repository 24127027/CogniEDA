# First-Class Objects

## Target Design

A First-Class Object is admitted only when it needs explicit identity, lifecycle, user-control semantics, retrieval policy, and epistemic role.

The canonical target FCO set is:

- `Objective`
- `DataProfile`
- `Assumption`
- `Task`
- `Hypothesis`
- `Evidence`
- `Discovery`
- `SessionFrame`

The target design explicitly excludes `Workspace`, `Question`, `AnalysisFrame`, `GeneratedView`, `PlannerOperation`, `ExecutionRun`, and `EvidenceCacheEntry` from the FCO set.

## Current Implementation Status

| Concept | Status | Current implementation |
| --- | --- | --- |
| `Objective` | Not implemented | Current code has `Project.objective` and `Project.research_questions`, but no `Objective` schema, table, repository, or lifecycle. |
| `DataProfile` | Partially implemented | `DataProfile` schema, table, repository, and profiler exist. Target fields such as direct DVC hash, lifecycle state, accepted ground truth, preprocessing history, and `immutable: true` are not fully modeled. Repository does not expose `update()`. |
| `Assumption` | Partially implemented | Schema, table, and repository exist. Current statuses are `active`, `validated`, `rejected`, `archived`, which differ from the target lifecycle. Testability admission is not enforced. Conclusion-context exclusion is implemented only for `SessionFrame` projection, not graph retrieval. |
| `Task` | Not implemented | No `Task` schema/table/repository exists. `SessionFrame.pending_tasks` stores strings only. |
| `Hypothesis` | Partially implemented | Schema, table, repository, and evidence evaluation links exist. Current model is not compiled from a terminal analytical `Task`, can link to multiple datasets, and lacks target fields such as `source_task_id`, `claim_type`, `evidence_expectation`, and `produced_discovery_id`. |
| `Evidence` | Partially implemented | Schema, table, and append-only repository exist. Current model stores result summary, parameters, provenance, limitations, and typed hypothesis evaluations. It lacks target `analysis_frame_ref`, lifecycle state, method IDs/hashes, environment hash, seed, execution run, and supersession fields. |
| `Discovery` | Not implemented | No schema, table, repository, or validity-envelope enforcement exists. |
| `SessionFrame` | Partially implemented | Schema, table, repository, and builder exist. Current implementation is a compact append-only snapshot. Target user-governed fields such as `pinned_object_ids`, `active_object_ids`, `excluded_object_ids`, ordered `context_items`, inclusion reasons, and audit notes are not implemented in the target form. |

## Current Non-Target Artifacts

| Current artifact | Status | Target-design note |
| --- | --- | --- |
| `Project` | Implementation deviates from target | Current root analytical container. Target design replaces research intent with `Objective` and treats workspace as the runtime boundary. |
| `DatasetAsset` | Implementation deviates from target | Current versioned dataset reference and lineage object. Target design says raw dataset is not a graph node and `DataProfile` stores dataset/version identity directly. |
| `DecisionLog` | Implementation deviates from target | Current persisted analytical decision artifact. Target design treats decisions as provenance/user decision records, not FCOs. |

## Target FCO Contract

Every target FCO must carry:

- explicit identity
- lifecycle state
- epistemic role
- provenance references
- authorization or user-control semantics
- retrieval policy

This is not currently encoded as a common base FCO class. Current Pydantic models use explicit IDs and timestamps, but do not all expose a target `type`, `epistemic_role`, `provenance_refs`, or `authorization_policy`.

## Admission Rule

Future FCO additions must first answer:

- Is this research intent, workflow state, data state, planning constraint, test contract, observed result, evidence-bound claim, or active context?
- Does it require its own lifecycle and user controls?
- Can it affect future reasoning, and in which context mode?
- Could it instead be provenance, cache, filesystem artifact, or generated view?

When uncertain, default to provenance or generated view rather than durable knowledge.
