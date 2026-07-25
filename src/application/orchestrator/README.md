# Remaining Application Orchestrator (`application.orchestrator`)

## 1. Purpose and current implementation

Following Package S2-B, `application.orchestrator` retains only genuine remaining cross-context Planner mutation coordination (`planner_commit.py`).

Discovery admission has been moved to `application.discovery`.
Validity propagation has been moved to `application.validity`.

### Remaining modules

| Module | Responsibility |
| --- | --- |
| `planner_commit.py` | Apply approved operations; atomic Planner mutation coordination. |

## 2. Forbidden responsibilities

- Execution attempt admission, dispatch, receipt, cancellation, retry, or recovery (owned by `application.execution`).
- AnalysisFrame or Evidence creation (owned by `application.evidence`).
- Protected evaluation bundle construction or evaluator runner (owned by `application.evaluation`).
- Governance authority issuance or decision recording (owned by `application.governance`).
- Discovery admission (owned by `application.discovery`).
- Validity propagation (owned by `application.validity`).

## 3. Moved in S2-B

- `atomic_discovery_admission.py` & `discovery_admission_coordinator.py` -> `application.discovery`
- `validity_propagation_service.py` -> `application.validity`
- `review_propagation.py` -> removed (subsumed by `AtomicValidityPropagationService`)

## 4. Tests

- `tests/application/orchestrator/test_package3_boundary.py`
