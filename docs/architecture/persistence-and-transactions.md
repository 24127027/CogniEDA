# Persistence and Transactions

> **Implementation status:** normalized ownership **Implemented**; transaction
> and trigger guarantees **Verified on SQLite**.

The reader-first Discovery transaction explanation is
[Governance and Discovery admission](../governance-and-discovery-admission.md).
The validity transaction explanation is
[Atomic validity propagation](../atomic-validity-propagation.md).
The canonical operational ownership explanation is
[Persistence and transaction ownership](../persistence-and-transaction-ownership.md).
This page retains package-level commit ownership and write sets.

## Layer separation

```text
domain schema != repository adapter != SQLModel table != migration asset
```

`schemas` owns typed values. `repositories` owns lookup/conversion and narrowly named staging
hooks. `db.models` owns the table-definition facade. `db.migrations` and
`db.legacy_migration` own SQLite upgrade and quarantine assets. Repositories do
not own the multi-record scientific commits. Private hooks stage effects in a
caller-owned session; ordinary public workflow writes and migration-only paths
are narrower, documented categories rather than alternate scientific owners.

## Table ownership

| Persistence module | Tables |
| --- | --- |
| `db.models.research` | objectives, objective_revisions, data_profiles, assumptions, tasks, hypotheses, session_frames |
| `db.models.workflow` | planner_operations |
| `db.models.execution` | execution_runs, execution_outbox, execution_inbox, execution_approvals |
| `db.models.evidence` | analysis_frames, evidence |
| `db.models.evaluation` | evaluation_controls |
| `db.models.governance` | user_decisions, governance_authorities, proposal_decisions |
| `db.models.discovery` | discoveries, discovery_admission_claims |
| `db.models.validity` | validity_events |

## Transaction write sets

| Operation | Commit owner | Principal write set |
| --- | --- | --- |
| approved Planner batch | `commit_planner_operations` | planner operation state plus Task, Objective/revision, Assumption, Hypothesis, or successor SessionFrame as requested |
| execution admission | `commit_planner_operations` delegating staging to `ExecutionAttemptTransitionService` | Hypothesis state, ExecutionRun, outbox, consumed approval, operation state |
| execution transitions | `ExecutionAttemptTransitionService` public methods and application execution coordinators | run, outbox, inbox, approval state as applicable |
| Evidence admission | `execute_evidence_admission_plan` | AnalysisFrame, Evidence, ExecutionRun, Hypothesis, authoritative inbox |
| evaluation lifecycle | `EvaluationTransitionService` | EvaluationControl |
| authority issuance | `GovernanceAuthorityIssuer` | GovernanceAuthority |
| proposal decision | `DiscoveryAdmissionGovernanceService` via its repository commit hook | ProposalDecision |
| Discovery admission | `AtomicDiscoveryAdmissionService` | Discovery, conclusion SessionFrame, Hypothesis, Task, EvaluationControl, admission claim, ProposalDecision |
| validity propagation | `AtomicValidityPropagationService` | source state, dependent Evidence/evaluation/claim/Discovery/Hypothesis/Task/SessionFrame state, ValidityEvent |

The phrase “sole writer” applies to a specific guarded transition, not every row of a table.
Atomic Discovery admission legitimately writes terminal EvaluationControl, Task, Hypothesis,
SessionFrame, claim, and decision fields. Atomic validity propagation legitimately writes validity
or review state across other contexts.

## Concurrency, replay, and limitations

Execution and scientific terminal paths use CAS conditions, lease/fencing epochs, deterministic
identities, exact fingerprints, or unique constraints. Evidence admission and Discovery admission
recognize exact committed replay; validity exact replay verifies the persisted complete effect
plan. Changed payloads/commands conflict. Failures roll back each owned transaction.

**Known deviation:** External Data Explorer side effects are at-least-once. Cross-service workflow
steps are not one distributed transaction. All concurrency and trigger claims are SQLite-only.
Python-private staging hooks, repository guards, architecture checks, and
selected database constraints form layered internal enforcement. Direct ORM or
SQL access can still bypass some supported-path rules and is not a hostile
database-access security boundary.
