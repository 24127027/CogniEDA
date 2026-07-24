# Canonical Investigation Workflow

> **Authority:** canonical target workflow.
> **Implementation status:** partially implemented; the current overlay below is evidence-backed.

## Target Flow

```text
user request
  -> Planner understands intent and manages/selects Task
  -> Graph Miner assembles governed Planning Context
  -> Hypothesis Analyst operationalizes one terminal analytical Task
  -> Planner validates readiness and obtains approval
  -> commit persists approved Hypothesis contract and execution intent atomically
  -> application creates the durable execution-attempt identity
  -> Data Explorer executes immutable contract and returns AnalysisFrame/Evidence observations
     plus bounded execution details, without durable attempt identity or evaluation authority
  -> application binds the durable ExecutionRun envelope and admits provenance and Evidence
  -> Hypothesis Analyst evaluates Evidence in Discovery Synthesis Context
  -> Graph Miner reviews lineage, staleness, contradiction and coverage
  -> Planner creates ordered PlannerOperations
  -> commit persists approved operations atomically
  -> Planner appends a SessionFrame with auditable inclusion reasons
```

Nodes may be combined for efficiency, but responsibility, typed inputs/outputs, approval, and
persistence boundaries must remain independently testable.

## Context Boundaries

Planning Context may contain active Assumptions and relevant prior Discoveries. Hypothesis
operationalization must label Assumptions as planning-only.

Discovery Synthesis Context contains only the approved Hypothesis, accepted DataProfile,
AnalysisFrame and ExecutionRun provenance, admitted Evidence, method/parameters, decision rule,
uncertainty, and validity metadata. It excludes Assumptions, existing Discoveries, Tasks, raw chat,
failed reasoning, caches, and unverified generated views. The local protected-evaluation path builds
the closed `DiscoverySynthesisBundle` from repositories and passes only that bundle to the
Hypothesis Analyst (`src/application/orchestrator/synthesis_bundle.py`,
`src/application/orchestrator/evaluator_runner.py`).

## Approval And Persistence Sequence

1. A proposal is typed and assigned a snapshot/fingerprint.
2. Pending workflow/proposal state is durable before it is exposed to the caller.
3. The user decision names the exact proposal and authorized action.
4. Deterministic code revalidates current Task, DataProfile, lineage, lifecycle, and authorization.
5. Commit applies the ordered batch in one transaction and records operation state.
6. External execution occurs only after the Hypothesis and execution intent are durable.
7. Result receipt is fenced and immutable; Evidence admission is a separate atomic transaction.

The current execution approval path implements steps 1-6 for its narrow contract
(`src/agents/planner/nodes.py:1599-1666`, `1833-1914`, `1151-1297`). Normal PlannerOperation commit
implements local all-or-nothing application (`src/application/orchestrator/planner_commit.py:79-156`).
Direct in-memory `APPROVED` non-Objective operations are not yet required to correspond to a
persisted approval record, so commit is not a universal authorization boundary.

## Current Implementation Overlay

| Stage | Current status | Evidence |
| --- | --- | --- |
| Understand request | Partially implemented | Explicit commands and PydanticAI structured classification exist; default tool configuration cannot assemble because configured MCP names are undefined (`src/agents/planner/nodes.py:82-190`, `config/agents.toml:4-22`, `config/mcp.toml:1-19`). |
| Manage/select Task | Partially implemented | `/manage_task` and `/decompose` produce typed, approval-gated operations; other planning branches are incomplete (`src/agents/planner/nodes.py:311-916`). |
| Graph Miner context | Partially implemented, misassigned | Bounded SQL-backed Discovery retrieval exists, but Graph Miner itself is a stub (`src/memory/retrieval_engine.py:38-205`, `src/agents/executor/graph_miner/graph.py:9-12`). |
| Hypothesis operationalization | Implemented but architecturally misaligned | Planner Task decomposition and `prepare_execution` compile the contract; Hypothesis Analyst is a stub (`src/agents/planner/types.py:357-483`, `src/agents/planner/nodes.py:971-1147`). |
| Approval/admission | Implemented narrow path | Durable approval, revalidation, Hypothesis/Run/outbox atomic admission (`src/agents/planner/nodes.py:1151-1297`, `1599-1914`). |
| Data Explorer execution | Contract and bootstrap implemented; adapter absent | The composition root requires explicit Data Explorer registration and does not register Graph Miner (`src/application/runtime.py`). |
| Result receipt | Implemented locally | Worker reconstructs durable identity and receiver stores a fenced digest (`src/application/orchestrator/dispatcher.py:27-134`, `receiver.py:16-76`). |
| Evidence production | Implemented locally | Canonical observations are materialized as AnalysisFrame/Evidence by the fenced atomic Evidence-admission transaction. |
| Evidence evaluation/Discovery | Implemented locally | Hypothesis Analyst evaluates only the protected bundle; an exact durable decision gates atomic Discovery admission. |
| Conflict/staleness review | Stub/partial utilities | Review nodes are placeholders; repository propagation and bounded retrieval provide only narrow signals (`src/agents/planner/nodes.py:1582-1595`, `src/application/orchestrator/review_propagation.py:13-48`). |
| Atomic commit | Implemented locally with gaps | Planner, Evidence admission, Discovery admission, and validity propagation use explicit atomic transactions; broader product effects remain out of scope. |
| SessionFrame update | Partially implemented | Objective, motivated Task/decomposition, and atomic Discovery admission append frames; general refresh and user item governance are absent. |

## Error And Retry Boundaries

- PydanticAI owns LLM structured-output validation and bounded model retries.
- LangGraph owns deterministic routing, interrupts, checkpoints, and resume state only.
- Application transition services own leases, fencing, result idempotency, cancellation, and
  technical retries (`src/application/orchestrator/transition_service.py`).
- Repositories and commit own domain validation and transaction rollback.
- A failed execution retains ExecutionRun/inbox provenance but creates no Evidence or Discovery
  (`src/application/orchestrator/finalizer.py:168-188`).
- A changed scientific contract requires a new governed proposal; it is not a technical retry.

## Runtime Entry-Point Reality

There is no supported package CLI, admission command, service API, or worker daemon.
`load_runtime_from_environment()` is a pure composition helper: it loads only an explicit
`COGNIEDA_RUNTIME_FACTORY=module:factory` hook and fails closed without deployment-provided
authentication, model, and Data Explorer adapters.
