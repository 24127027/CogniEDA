# CogniEDA Project Purpose and Epistemic Core

> **Implementation status:** The research-state core, protected scientific admission paths, and their SQLite transaction semantics are implemented. Product bootstrap, concrete executor/model adapters, DVC, cache, and several Planner branches remain partial or absent.

CogniEDA is a **governed research-state system for analytical investigation**. It bridges the critical gap between ungrounded natural-language reasoning and rigorous data analysis by providing validity-preserving research-state infrastructure.

---

## 1. The Core Problem

Standard AI tools for data analysis suffer from fundamental architectural flaws:
1. **Memory Confusion**: They treat conversation logs, raw chat history, and vector embeddings as durable domain knowledge.
2. **Epistemic Drift**: Assumptions made early in a conversation silently leak into later scientific inferences as if they were proven facts.
3. **Invalidation Blindness**: When underlying data or method parameters change, previously generated conclusions are not tracked or invalidated, leading to invalid analytical conclusions.
4. **Lack of Authority Boundaries**: Code execution tools double as scientific proposal authors, generating unstructured prose summaries instead of traceable, evidence-bound claims.

---

## 2. The Core Thesis: Validity-Preserving Research State

CogniEDA solves these failures by enforcing a **typed, governed, validity-preserving research-state model**.

Priority Order of Invariants:
1. **Conclusion Validity and Traceability**: Every claim (`Discovery`) must be deterministically bound to immutable observed `Evidence` generated from an audited execution on a specific `DataProfile`.
2. **Context Type Safety**: Strict type boundaries prevent `Assumption` objects, raw conversation history, or rejected tasks from entering scientific synthesis contexts.
3. **Multi-Session Continuity**: Research state is durable across sessions using structured First-Class Objects (FCOs) persisted in a single-writer relational database (SQLite).

---

## 3. Epistemic Classification

CogniEDA strictly separates objects by their structural and epistemic roles:

| Category | Description | Primary Objects |
| :--- | :--- | :--- |
| **First-Class Objects (FCOs)** | Core domain entities possessing durable identity, lifecycle, and strict governance | `Objective`, `DataProfile`, `Assumption`, `Task`, `Hypothesis`, `Evidence`, `Discovery`, `SessionFrame` |
| **Provenance Records** | Audit trails of analytical computation and workflow execution | `AnalysisFrame`, `ExecutionRun`, `ExecutionApproval`, `ExecutionInbox`, `ExecutionOutbox` |
| **Workflow State** | Durable or transient coordination state that is not scientific knowledge | `PlannerOperation`, `TaskProposal`, `UserDecision`, `EvaluationControl` |
| **Generated Views** | Derived visual or analytical output representations | Plots, summary tables, dynamic UI artifacts |
| **Cache & Indexes** | Query/retrieval acceleration structures, not scientific writers | Target cache/index surfaces; no persistent cache or semantic index is implemented |

---

## 4. What CogniEDA Is Not

To preserve architectural integrity, CogniEDA is explicitly **not**:
* A generic EDA chatbot or long-memory chat agent.
* A vector-store retrieval assistant.
* An autonomous unguided scientific agent.
* A generic multi-agent framework wrapper.
* A Jupyter notebook UI overlay.

---

## 5. Architectural Entry Points

* Architecture Overview: [overview.md](architecture/overview.md)
* Scientific Authority: [scientific-specialist-contracts.md](architecture/scientific-specialist-contracts.md)
* Research State Model: [research-state-model.md](architecture/research-state-model.md)
* Structural Exit Status: [structural-exit-status.md](architecture/structural-exit-status.md)
