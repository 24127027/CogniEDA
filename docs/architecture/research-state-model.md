# Research-State Model & First-Class Objects (FCOs)

> **Status**: `[Implemented]` / `[Verified on SQLite]`

This document defines the canonical **First-Class Objects (FCOs)**, provenance entities, and runtime structures in CogniEDA.

---

## 1. Target First-Class Objects (FCOs)

Only the following 8 entities are target First-Class Objects in CogniEDA:

| FCO | Epistemic Role | Lifecycle / Mutability | Sole Write Authority | Read / Retrieval Policy |
| :--- | :--- | :--- | :--- | :--- |
| **Objective** | High-level research motivation & scientific goal | Mutable via versioned revisions (`ObjectiveRevision`) | `ObjectiveRepository` / Commit Service | Unrestricted |
| **DataProfile** | Formal specification & statistical fingerprint of a dataset version | Immutable | Data Profiler / Dataset Import | Active ground-truth profile included in planning |
| **Assumption** | Stated analytical premise or user heuristic | Mutable (Active, Superseded, Flagged) | Planner Commit / User Action | **Quarantined** from Conclusion/Synthesis context |
| **Task** | Analytical work item decomposing an Objective | State machine (`DRAFT`, `PENDING_APPROVAL`, `READY`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`) | Task Repository / Execution Transition | Planning and context resolution |
| **Hypothesis** | Testable mathematical/statistical assertion bound 1:1 to a terminal Task | State machine (`PROPOSED`, `EVALUATED`, `INVALIDATED`) | Task Commit / Admission Service | Conclusion Synthesis Context |
| **Evidence** | Observed empirical result from audited execution | **Immutable** | `EvidenceAdmissionService` | Conclusion Synthesis Context |
| **Discovery** | Evidence-bound scientific claim | **Immutable** | `AtomicDiscoveryAdmissionService` | Default active retrieval (if valid) |
| **SessionFrame** | Active user context & focal window | Updated on user interaction | `SessionFrameRepository` | Active retrieval boundary |

---

## 2. Non-FCO Boundaries

The following entities are explicitly **not** First-Class Objects:
- **`Workspace`**: Filesystem & runtime boundary.
- **`Question`**: User UI input that decomposes into a `Task`.
- **`AnalysisFrame`**: Provenance & dataset view metadata record.
- **`ExecutionRun`**: Provenance & execution attempt record.
- **`GeneratedView`**: Runtime visualization output.
- **`PlannerOperation`**: Pending state mutation proposal.
- **`EvidenceCacheEntry`**: Transient performance cache.

---

## 3. Structural Invariants & Lifecycles

1. **`DataProfile` Immutability**: Cleaning or transforming data creates a *new dataset version* and a *new `DataProfile`*. Existing profiles are never mutated.
2. **`Evidence` Immutability**: Analytical results cannot be updated. Overwritten or superseded results create new `Evidence` records and trigger invalidation events.
3. **One-to-One Task & Hypothesis Binding**: One terminal analytical `Task` produces exactly one `Hypothesis`. Parent tasks do not produce hypotheses or discoveries.
4. **`Discovery` Materialization Requirement**: A `Discovery` cannot exist without backing `Evidence`. It must contain structured `claim`, `scope`, and `validity_basis`.
5. **Assumption Quarantine**: `Assumption` objects may guide planning but are strictly excluded from Conclusion and Discovery Synthesis contexts.
