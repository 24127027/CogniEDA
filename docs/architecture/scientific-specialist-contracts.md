# Scientific Specialist Contracts & Authority Boundaries

> **Status**: `[Implemented]` / `[Verified on SQLite]`

This document defines the authority boundaries, input/output contracts, and responsibility matrix for CogniEDA's specialist roles.

---

## 1. Scientific Responsibility Matrix

| Role / Component | Observation Authority | Evaluation Authority | Proposal Authority | Decision Authority | Persistence Authority | Invalidation Authority |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Data Explorer** | **YES** | NO | NO | NO | NO | NO |
| **Hypothesis Analyst** | NO | **YES** | **YES** | NO | NO | NO |
| **Application Services** | NO | NO | NO | NO | **YES** | **YES** |
| **User Governance** | NO | NO | NO | **YES** | NO | NO |

---

## 2. Data Explorer Boundary

**Authority**:
- Executes sandboxed code against `DataProfile`.
- Emits `AnalysisFrameObservation` and `EvidenceObservation`.
- Emits technical failure results and diagnostics.

**Explicit Exclusions**:
- Must **not** evaluate a `Hypothesis`.
- Must **not** create a `DiscoveryProposal`.
- Must **not** record governance decisions.
- Must **not** mutate database models.

---

## 3. Hypothesis Analyst Boundary

**Authority**:
- Evaluates backing `Evidence` against a `Hypothesis` decision rule.
- Author of scientific claim proposals: produces `DiscoverySynthesisBundle` $\rightarrow$ `DiscoveryProposal | EvaluationFailure`.

**Protected Context Inclusions**:
- Target `Hypothesis`.
- Active `DataProfile`.
- `AnalysisFrame` provenance.
- Backing `Evidence` records.
- Method parameters and decision rules.

**Protected Context Exclusions**:
- **Assumptions** (Strictly Quarantined).
- Prior `Discovery` objects.
- `SessionFrame` context.
- Conversation history / chat prose.
- Retrieval scores / arbitrary context bags.

---

## 4. Governed Proposal-Copy Rule

When the Hypothesis Analyst generates a `DiscoveryProposal`, application services enforce the **Exact Proposal-Copy Rule**:
- The proposal digest (`proposal_digest`) is calculated via SHA-256 over the claim payload.
- Governance records a `UserDecision` linked to this exact proposal digest.
- `AtomicDiscoveryAdmissionService` verifies that the materializing `Discovery` is an exact structural copy of the authorized proposal before committing.
