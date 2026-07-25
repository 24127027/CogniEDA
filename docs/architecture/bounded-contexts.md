# Bounded Contexts & Package Architecture

> **Status**: `[Implemented]` / `[Verified on SQLite]`

CogniEDA is structured into explicit bounded contexts across application services, schemas, repositories, and persistence models.

---

## 1. Canonical Bounded-Context Map

```text
src/
├── application/
│   ├── research/       (Objective, Task, Hypothesis lifecycle)
│   ├── execution/      (ExecutionTransitionService, sandbox dispatch)
│   ├── evidence/       (EvidenceAdmissionService)
│   ├── evaluation/     (EvaluationControlService, Hypothesis Analyst runner)
│   ├── governance/     (ProposalDecisionService, UserDecision)
│   ├── discovery/      (AtomicDiscoveryAdmissionService)
│   ├── validity/       (AtomicValidityPropagationService)
│   ├── orchestrator/   (Planner commit & transaction orchestration)
│   ├── events/         (Domain event pub/sub dispatcher)
│   └── bootstrap/      (Runtime composition & factory registry)
│
├── schemas/
│   ├── research/       (Objective, Task, Hypothesis value objects)
│   ├── execution/      (ExecutionDetails, PreparedExecution, observations)
│   ├── evidence/       (Evidence value objects & admission contracts)
│   ├── evaluation/     (EvaluationControl, synthesis bundle schemas)
│   ├── governance/     (GovernanceAuthority, ProposalDecision schemas)
│   ├── discovery/      (Discovery, claim, & admission contracts)
│   └── validity/       (ValidityEvent & propagation contracts)
│
├── repositories/
│   ├── research/       (Objective, Task, Hypothesis, Assumption repos)
│   ├── execution/      (ExecutionRun, Inbox, Outbox repos)
│   ├── evidence/       (AnalysisFrame, Evidence repos)
│   ├── evaluation/     (EvaluationControl repo)
│   ├── governance/     (GovernanceAuthority, ProposalDecision repos)
│   ├── discovery/      (Discovery, AdmissionClaim repos)
│   └── validity/       (ValidityEvent repo)
│
└── db/
    └── models/         (Stable SQLModel database facade)
        ├── research.py
        ├── execution.py
        ├── evidence.py
        ├── workflow.py
        ├── evaluation.py
        ├── governance.py
        ├── discovery.py
        ├── validity.py
        └── common.py
```

---

## 2. Dependency Direction Invariants

1. **Schemas**: Dependency-inert value objects. Import no application or repository code.
2. **Repositories**: Persistence adapters. Import schemas and `db.models`. Import no application code.
3. **Application Services**: Core domain logic and transactions. Import schemas and repositories.
4. **Specialists (Data Explorer / Analyst)**: Pure computational agents. Do not import database models, repositories, or application transaction services.
5. **Facade Protection**: All database operations use `db.models` facade exports. Direct imports from submodules or schema compatibility aliases are forbidden.
