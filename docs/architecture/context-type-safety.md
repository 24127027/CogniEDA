# Context Type Safety & Assumption Quarantine

> **Status**: `[Implemented]` / `[Verified on SQLite]`

CogniEDA enforces context type safety across all planning, execution, synthesis, and retrieval contexts to prevent epistemic pollution.

---

## 1. Defined Context Types

| Context Type | Purpose | Allowed Objects | Forbidden Objects |
| :--- | :--- | :--- | :--- |
| **Planning Context** | Decomposing research goals into task plans | `Objective`, `DataProfile`, `Assumption`, active `Task` tree, `SessionFrame` | Unverified executions, rejected tasks |
| **Execution Context** | Sandboxed execution of analytical code | `Task`, `DataProfile`, execution parameters, seed | `Assumption`, raw chat history, prior discoveries |
| **Conclusion Context** | Scientific synthesis & discovery evaluation | `Hypothesis`, `DataProfile`, `AnalysisFrame`, backing `Evidence` | **`Assumption`**, prior `Discovery` objects, chat history, retrieval scores |
| **Governance Context** | User review & decision recording | `DiscoveryProposal`, `EvaluationControl`, `GovernanceAuthority` | Unverified proposals, direct FCO mutators |
| **Retrieval Context** | Workspace context resolution | Active `SessionFrame`, non-invalidated `Discovery` objects | Invalidated objects, stale session frames, rejected tasks |

---

## 2. Assumption Quarantine Mechanism

The core invariant of context type safety is the **Assumption Quarantine**:
- `Assumption` objects represent user premises, heuristics, or unverified domain beliefs.
- While `Assumption`s are accessible during **Planning Context** to help structure tasks, they are **strictly excluded** from **Conclusion Context**.
- Scientific evaluation of a `Hypothesis` relies solely on empirical `Evidence` and verified `DataProfile` attributes.
- After a `Discovery` is materialized, it may be compared against active `Assumption`s to flag contradictions, but the `Assumption` cannot serve as an inference premise.
