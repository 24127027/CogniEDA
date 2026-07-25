# Package S4 Structural Exit Status

> **Status:** `[Implemented]` after Codex adversarial repair.
>
> **Final verdict:** `PASS WITH EXPLICIT LIMITATIONS`
>
> **Package 7 readiness:** `READY WITH EXPLICIT LIMITATIONS`

## Verified baseline and candidate

| Item | Result |
| --- | --- |
| required S3-B baseline | `4c39a71b5dec28aa3e9886e4e60ecb676d68e2a8` |
| Gemini S4 commit | `8ced3c42bc31a01cf3753a0a0af61327d27a24e0` |
| table facade | 21 SQLModel tables |
| SQLite metadata | 214 non-internal `sqlite_master` objects; 10 triggers |
| persistence support | SQLite only |

Final command results and the final repair SHA are recorded in the ignored local audit:
`.local/audits/package-s4-documentation-reconstruction-structural-exit.md`.

## Structural context map

| Context | Canonical owner | Transaction owner | Runtime path | Verification | Known deviation |
| --- | --- | --- | --- | --- | --- |
| research/workflow | research schemas/repos/models; Planner operations | `commit_planner_operations` | `Planner.run` | planner/repository/architecture tests | Planner nodes open sessions and persist approval state |
| execution | `application.execution` | `ExecutionAttemptTransitionService` and execution coordinators | runtime dispatch/reconcile; finalizer | execution/race/recovery tests | no worker process; external effects at-least-once |
| evidence | `application.evidence` | `execute_evidence_admission_plan` | execution finalizer | Evidence admission tests | no concrete Data Explorer |
| evaluation | `application.evaluation` | `EvaluationTransitionService` | runtime evaluation | bundle/runner/transition tests | deployment must supply model |
| governance | `application.governance` | `GovernanceAuthorityIssuer`; `DiscoveryAdmissionGovernanceService` | runtime authority/decision methods | governance/race tests | deployment must supply authentication |
| discovery | `application.discovery` | `AtomicDiscoveryAdmissionService` | runtime coordinator | atomic admission/E2E tests | SQLite-only locking and triggers |
| validity | `application.validity` | `AtomicValidityPropagationService` | runtime facade | validity/concurrency tests | authority issuer exists; deployment authentication remains external |
| retrieval/session | `memory`; research/discovery repositories | append paths and validity service | Planner decomposition/library calls | memory/validity tests | no Graph Miner, vector index, or resume UI |

## Scientific authority and transaction result

Data Explorer is observation-only. Hypothesis Analyst alone authors typed proposal wording from a
closed bundle. Governance records exact authority/decisions. Atomic Discovery admission alone
materializes the authorized proposal and terminal chain. Atomic validity propagation alone issues
validity events and applies their complete dependency plan. Repositories do not own those
multi-record transactions.

## Planner persistence-access classification

**Decision:** `NON-BLOCKING DOCUMENTED DEBT`.

Planner modules have:

- read-only application access through short-lived sessions;
- direct durable orchestration of execution and PlannerOperation approvals;
- durable PlannerOperation staging and calls to `commit_planner_operations`;
- application-service mutation of approved Objective, Task, Assumption, Hypothesis, and successor
  SessionFrame state;
- execution admission delegated to `ExecutionAttemptTransitionService`;
- explicit fail-closed handlers for generic AnalysisFrame, Evidence, Discovery, inbox, and
  unsupported execution-run mutations.

No supported Planner path can create Evidence or Discovery, mark scientific terminal state, or
bypass established scientific transaction services. The coupling is architectural debt because
Planner nodes know SQLModel sessions, repositories, `db.models`, and commit orchestration. Moving
that access behind a Planner application facade is recommended, but it does not require a
pre-Package-7 redesign.

## Explicit limitations

- no supported CLI/API/worker/daemon;
- no production authentication, model, or Data Explorer adapter;
- Planner answer/suggest/pause/conflict/assumption branches remain incomplete;
- Planner still authors the analytical contract;
- SessionFrame governance/resume is partial;
- Graph Miner, persistent semantic index, DVC execution, cleaning workflow, and cache are absent;
- strict mypy remains baseline technical debt;
- SQLite is the only verified database.

These limitations constrain product scope but do not leave an unclosed scientific-authority bypass
on the supported in-process paths.
