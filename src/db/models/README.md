# CogniEDA SQLModel Persistence Models (`db.models`)

## 1. Purpose

This package owns SQLModel table definitions for all persisted CogniEDA research-state and provenance records.

The `db.models` package acts as the explicit persistence facade for the repository. Importing `db.models` registers all 21 table models in `SQLModel.metadata`.

## 2. Model Ownership by Bounded Context

| Bounded Context | Model Class | Database Table (`__tablename__`) | Primary Key |
| --- | --- | --- | --- |
| **Research** | `ObjectiveRecord` | `objectives` | `objective_id` |
| | `ObjectiveRevisionRecord` | `objective_revisions` | `revision_id` |
| | `DataProfileRecord` | `data_profiles` | `profile_id` |
| | `AssumptionRecord` | `assumptions` | `assumption_id` |
| | `TaskRecord` | `tasks` | `task_id` |
| | `HypothesisRecord` | `hypotheses` | `hypothesis_id` |
| | `SessionFrameRecord` | `session_frames` | `session_frame_id` |
| **Execution** | `ExecutionRunRecord` | `execution_runs` | `execution_run_id` |
| | `ExecutionOutboxRecord` | `execution_outbox` | `outbox_id` |
| | `ExecutionInboxRecord` | `execution_inbox` | `inbox_id` |
| | `ExecutionApprovalRecord` | `execution_approvals` | `approval_id` |
| **Evidence** | `AnalysisFrameRecord` | `analysis_frames` | `analysis_frame_id` |
| | `EvidenceRecord` | `evidence` | `evidence_id` |
| **Evaluation** | `EvaluationControlRecord` | `evaluation_controls` | `evaluation_id` |
| **Governance** | `UserDecisionRecord` | `user_decisions` | `decision_id` |
| | `GovernanceAuthorityRecord` | `governance_authorities` | `authority_id` |
| | `ProposalDecisionRecord` | `proposal_decisions` | `decision_id` |
| **Discovery** | `DiscoveryRecord` | `discoveries` | `discovery_id` |
| | `DiscoveryAdmissionClaimRecord` | `discovery_admission_claims` | `claim_id` |
| **Validity** | `ValidityEventRecord` | `validity_events` | `event_id` |
| **Workflow** | `PlannerOperationRecord` | `planner_operations` | `operation_id` |

## 3. Shared Persistence Value Objects

- `TimestampedRecord`: Base class for records carrying indexed `created_at` and `updated_at` timestamps.
- `utc_now`: Standardized helper returning timezone-aware UTC datetime instances.

Both are owned strictly by `db.models.common` to prevent duplicate persistence definitions.

## 4. Invariants and Facade Safety

1. **Exact Table Registration**: Exactly 21 `table=True` classes are defined across 8 bounded model modules (`research`, `execution`, `evidence`, `evaluation`, `governance`, `discovery`, `validity`, `workflow`).
2. **Facade Re-export**: `db.models.__init__.py` re-exports all 21 table classes plus `TimestampedRecord` and `utc_now` in `__all__`.
3. **Import Order Safety**: Importing `db.models` or importing individual bounded model modules in any order registers the exact same set of 21 tables in `SQLModel.metadata`.
4. **No Alternate Writers**: Database models contain no application write logic or transaction handling.
