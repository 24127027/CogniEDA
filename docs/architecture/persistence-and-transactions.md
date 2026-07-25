# Persistence & Transaction Boundaries

> **Status**: `[Implemented]` / `[Verified on SQLite]`

CogniEDA enforces explicit, isolated write sets and single-owner transactions for all database operations.

---

## 1. Canonical Storage Architecture

- **Engine**: SQLite with WAL (Write-Ahead Logging) and immediate transaction locking.
- **ORM / DDL Layer**: SQLModel over SQLAlchemy core.
- **Facade Import Boundary**: `src/db/models/__init__.py` acts as the sole public persistence model facade.

---

## 2. Table Set & Transaction Owners

| Table Name | Entity Description | Sole Transaction Owner | Write Boundary / Mutability |
| :--- | :--- | :--- | :--- |
| `objectives` | Research objectives | Objective Commit Service | Mutable via `objective_revisions` |
| `objective_revisions` | Revision audit log | Objective Commit Service | Append-only |
| `data_profiles` | Dataset fingerprints | Data Profiler Service | **Immutable** |
| `assumptions` | Research premises | Planner Commit Service | Mutable lifecycle state |
| `tasks` | Analytical work items | Task Commit / Transition Service | State machine updates |
| `hypotheses` | Testable hypotheses | Task Commit / Transition Service | State machine updates |
| `execution_runs` | Execution attempt record | `ExecutionTransitionService` | Fenced lease & state updates |
| `execution_inbox` | Dispatch queue | `ExecutionTransitionService` | Monotonic status updates |
| `execution_outbox` | Completion queue | `ExecutionTransitionService` | Monotonic status updates |
| `execution_approvals` | Sandbox approval tokens | `ExecutionTransitionService` | Fenced consumption |
| `analysis_frames` | Provenance records | `EvidenceAdmissionService` | **Immutable** |
| `evidence` | Observed empirical results | `EvidenceAdmissionService` | **Immutable** |
| `evaluation_controls` | Synthesis control records | `EvaluationControlService` | State machine updates |
| `governance_authorities` | User authority tokens | `ProposalDecisionService` | **Immutable** (Trigger guarded) |
| `proposal_decisions` | Recorded user decisions | `ProposalDecisionService` | Monotonic consumption (Trigger guarded) |
| `discovery_admission_claims` | Fenced materialization claims | `AtomicDiscoveryAdmissionService` | Terminal state updates (Trigger guarded) |
| `discoveries` | Materialized claims | `AtomicDiscoveryAdmissionService` | **Immutable** |
| `session_frames` | Active focal windows | Session Service | Mutable focal context |
| `planner_operations` | Staged operations | Planner Commit Service | Pending operations queue |
| `user_decisions` | Direct decision log | Governance Service | Append-only |
| `validity_events` | Invalidation audit trail | `AtomicValidityPropagationService` | **Immutable** (Trigger guarded) |

---

## 3. Atomic Transaction Write Sets

### Execution Transition Write Set
- Owner: `ExecutionTransitionService`
- Write Set: `ExecutionRunRecord`, `ExecutionInboxRecord`, `ExecutionOutboxRecord`, `ExecutionApprovalRecord`.

### Evidence Admission Write Set
- Owner: `EvidenceAdmissionService`
- Write Set: `AnalysisFrameRecord`, `EvidenceRecord`, `TaskRecord` (status update).

### Discovery Admission Write Set
- Owner: `AtomicDiscoveryAdmissionService`
- Write Set: `DiscoveryRecord`, `DiscoveryAdmissionClaimRecord`, `EvaluationControlRecord` (`COMMITTED`), `ProposalDecisionRecord` (`consumed=1`).

### Validity Propagation Write Set
- Owner: `AtomicValidityPropagationService`
- Write Set: `ValidityEventRecord`, `HypothesisRecord` (`INVALIDATED`), `DiscoveryAdmissionClaimRecord` (`INVALIDATED`), `AnalysisFrameRecord` (`INVALIDATED`).
