# Runtime Composition & In-Process Architecture

> **Status**: `[Implemented]` / `[Verified on SQLite]`

This document describes the in-process execution environment, runtime composition, and current entry point limitations of CogniEDA.

---

## 1. `CogniEDARuntime` Composition

The application is assembled in-process via `CogniEDARuntime` (`src/application/bootstrap/runtime.py`):

```python
class CogniEDARuntime:
    """In-process composition facade for CogniEDA application services."""
```

Component Wiring:
- **Database Connection**: Configures SQLite database engine with WAL mode and immediate locking.
- **Registry Services**: Manages Data Explorer capability registration.
- **Service Layer Wiring**: Instantiates `ExecutionTransitionService`, `EvidenceAdmissionService`, `EvaluationControlService`, `ProposalDecisionService`, `AtomicDiscoveryAdmissionService`, and `AtomicValidityPropagationService`.

---

## 2. In-Process Runtime Guarantees

1. **Deterministic Execution**: All execution runs record parameters, random seeds, and method IDs.
2. **Atomic State Transitions**: Mutating state transitions run within guarded database transaction blocks.
3. **Restart Reconstruction**: Workspaces can be reloaded directly from SQLite database state without losing lineage or validity history.

---

## 3. Product & Entry Point Limitations

> [!WARNING]
> **No Supported CLI or HTTP Service Currently Exists**:
> CogniEDA is currently an **in-process Python library**. There is **no production CLI binary**, HTTP REST API, gRPC service, or async background worker daemon. Production entry points will be introduced in Package 7. Internal test runners must not be used as product interfaces.
