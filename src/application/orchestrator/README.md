# Durable Execution Orchestrator

## Current implementation

This package does not contain a generic request orchestrator. It implements the durable Wave 1
execution, Evidence evaluation, Discovery governance, admission, and validity path:

| Module | Current responsibility |
| --- | --- |
| `execution_contracts.py` | Validate/revalidate prepared planner execution contracts. |
| `execution_admission.py` | Build the typed PlannerOperation admission bundle. |
| `planner_commit.py` | Apply approved operations; special-case atomic execution/scientific bundles. |
| `transition_service.py` | Sole owner of attempt admission, CAS, lease, fencing, cancellation and recovery writes. |
| `dispatcher.py` | Claim pending outbox attempts and call an injected executor. |
| `receiver.py` | Canonicalize/digest results and persist them through the transition owner. |
| `finalizer.py` | Historical filename for the restart-safe, fenced Evidence-admission coordinator; it creates AnalysisFrame/Evidence only and has no evaluation or Discovery authority. |
| `evidence_admission.py` | Validate canonical Data Explorer observations and atomically stage AnalysisFrame/Evidence plus attempt/inbox transitions. |
| `evaluator_runner.py` | Claim a protected bundle evaluation and publish only a typed proposal or failure. |
| `discovery_admission_governance.py` | Bind an exact proposal to independently issued, durable decision authority. |
| `atomic_discovery_admission.py` | Sole writer for Discovery, decision consumption, evaluation commit, Hypothesis/Task terminal transitions, and conclusion SessionFrame. |
| `validity_propagation_service.py` | Sole writer for validity propagation and dependent invalidation/review state. |
| `reconciler.py` | Retry pending Evidence admission and handle expired leases. |
| `cancellation.py` | Thin cancellation, release and retry APIs over the transition service. |

There are no `application_orchestrator.py`, `request_pipeline.py` or `response_pipeline.py` files.

## Known deviations

- Technical retry reuses the existing Hypothesis and creates one successor `ExecutionRun`; a database constraint prevents direct-successor fan-out. A retry of a failed successor must target that successor, not the original attempt.
- Execution admission validates one matching `ExecutionRun`/outbox pair before staging either row. This is a narrow attempt-contract boundary, not a general executor-contract redesign.
- The composition root exposes dispatcher, reconciler, evaluator and admission services, but no
  process/worker loop invokes them automatically.
- External executor side effects remain at-least-once.
- Concrete Data Explorer implementations and production auth/model adapters are deployment
  requirements and are not checked in.
- The `finalizer.py` filename and persisted `finalizer_*` SQLite columns are retained physical
  migration compatibility names. Active statuses and behavior are Evidence-admission-specific;
  `FINALIZING` and ambiguous run `COMPLETED` are migration-only legacy values.
