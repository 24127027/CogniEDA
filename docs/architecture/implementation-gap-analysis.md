# Implementation Gap Analysis

> **Current implementation snapshot:** Package S1-B review candidate, 2026-07-25.
> Code is the source of truth for current behavior. Local verification audits under
> `.local/audits/` are ignored working records, not clean-clone documentation authority.

## Current Implementation Versus Target

| Area | Target | Current implementation | Status / principal gap |
| --- | --- | --- | --- |
| FCO ontology | Exactly Objective, DataProfile, Assumption, Task, Hypothesis, Evidence, Discovery, SessionFrame | Pydantic schemas, SQLModel tables and repositories use this set | Implemented locally; no production graph abstraction |
| Planner governance | Understand, route, manage Tasks/Objectives/Assumptions/approvals, coordinate specialists, emit operations | Request classification and narrow Task/decomposition/Objective/execution approvals exist | Partial; answer/suggest/review/pause and several approval workflows are placeholders |
| Hypothesis Analyst | Operationalize Task and evaluate Evidence in protected context without raw-data access | A no-tool PydanticAI evaluation mode consumes only a canonical repository-built bundle and durably publishes a fenced proposal/failure; Planner still authors the operational contract | Evidence evaluation implemented; operationalization ownership remains misaligned |
| Data Explorer | Execute approved contract and return observation-only provenance/Evidence inputs | Contract, dispatcher, and per-runtime factory registration exist; no concrete implementation is checked in | Partial boundary; concrete adapter absent |
| Graph Miner | Typed graph retrieval, lineage/staleness/conflict/coverage analysis | Stub wrapper plus separate bounded SQL-backed Discovery retrieval | Partial and misassigned |
| PydanticAI boundary | Canonical LLM construction, deps, tools, typed output, validation and retry | Used by selected Planner adapters; default checked-in tool config fails assembly | Partial / configuration-blocked |
| LangGraph boundary | Deterministic routing, interruption, checkpoint and workflow state only | Planner topology uses it; Hypothesis Analyst evaluation uses PydanticAI directly, while Graph Miner remains a stub and `DataExplorerAdapter` owns observation-output validation | Retain narrowly; Graph Miner and concrete Data Explorer remain absent |
| Task/Hypothesis/Discovery lineage | Active terminal Task -> one Hypothesis -> active Evidence -> one Discovery | Repository constraints plus atomic Evidence and Discovery admission enforce cardinality and sole terminal writers | Implemented locally |
| Approval | Exact durable proposal and user decision before governed mutation/execution | Public Task/decomposition/Objective and execution paths bind exact proposals | Partial; commit can trust caller-authored in-memory approval for other operations |
| Atomic commit | Approved ordered operations and validity changes persist all-or-nothing | Planner, Evidence admission, finalization, validity propagation and Discovery admission each use an application-owned atomic transaction | Implemented for these local SQLite paths; broader cross-service effects remain outside one transaction |
| Execution attempts | Durable outbox/inbox, fencing, idempotency, cancellation, retry | Transition service and race/recovery tests exist | Implemented locally; no worker bootstrap and external effects remain at-least-once |
| Evidence admission | Observation-only, deterministic AnalysisFrame/Evidence materialization in one fenced transaction | Active execution finalization routes through fenced transaction, materializes AnalysisFrame and Evidence, advances ExecutionRun to `EVIDENCE_ADMITTED` and Hypothesis to `READY_FOR_EVALUATION` in one atomic commit with zero automatic Discovery creation | Implemented (Package 1 Cutover); active production path terminates at durable Evidence |
| Execution/Evidence bounded contexts | Execution coordination, Evidence admission, and canonical execution schemas have separate owners | `application.execution`, `application.evidence`, and `schemas.execution` are active; old orchestrator/schema paths and compatibility exports are removed | Implemented by S1-B; remaining evaluation/governance/Discovery/validity decomposition is deferred to S2/S3 |
| Context type safety | Assumptions only in planning; protected Discovery synthesis | Package 2 builds immutable repository-authoritative evaluation snapshots, a closed provenance manifest, and a complete digest; the Analyst receives only that bundle | Implemented for Hypothesis evaluation; broader Graph Miner and generated-view context remain absent |
| Discovery admission governance | Exact persisted proposal and independently authorized decision produce one atomic Discovery chain | Package 5 resolves authenticated principal context through an injected adapter, persists an exact decision, durably claims admission, reconstructs under the SQLite writer lock, and atomically commits Discovery plus lifecycle, decision, claim and conclusion-frame companions | Implemented locally for SQLite; the product composition root still needs a real authentication adapter |
| Validity propagation | One authorized source event atomically invalidates every applicable dependent and current retrieval path | Package 4 supports eight typed DataProfile, AnalysisFrame, Evidence, ExecutionRun, conflict, supersession, invalidation, and provenance-corruption events through one fenced transaction and immutable event record | Implemented locally; no production authority issuer, only explicit SQLite upgrade/trigger support |
| SessionFrame | User-governed current context with auditable item inclusion | Append snapshots, narrow successor updates and deterministic atomic conclusion frames exist | Partial; no item governance, session scoping/cardinality or general refresh |
| Provenance | Reproducible data view, method, code, environment, seed, artifacts | Minimal AnalysisFrame/ExecutionRun and Evidence refs | Partial; insufficient for general reproducibility/invalidation |
| Dataset versioning/cleaning | DVC/physical versions and approved cleaning produce new DataProfile | CSV/Parquet profiler plus DVC interface | Partial; DVC and cleaning execution absent |
| Retrieval/graph | Durable FCO relations and governed Graph Miner traversal | SQLModel/JSON relations and bounded Discovery retrieval | Partial; no graph-store abstraction or Graph Miner workflow |
| Evidence cache | Validity-keyed reuse that cannot author Discovery | No table/service | Absent |
| Product surface | Supported CLI/service/worker loop | Package 6 provides a fail-closed in-process composition root and pure environment loader; no supported CLI, API, or worker process exists | Partial; concrete deployment adapters and product surfaces are absent |
| Quality gates | Reproducible pytest, lint, format, type, import/startup, migration checks in CI | Extensive local tests and documented repository commands exist; no tracked CI and strict mypy debt remains | Partial |

## Protected Invariants Already Present

- Frozen DataProfile/Evidence Pydantic payloads and append-oriented repositories
  (`src/schemas/common.py:82-90`, `src/schemas/artifacts.py:74-96`, `206-234`).
- Only active terminal analytical Tasks using an accepted DataProfile admit a Hypothesis; unique
  Task/Hypothesis and Hypothesis/Discovery constraints exist
  (`src/repositories/hypothesis_repository.py:56-92`, `src/db/models.py:212-229`, `429-466`).
- Atomic Discovery admission requires active same-Hypothesis Evidence and structured validity
  metadata; the generic repository writer is sealed
  (`src/application/orchestrator/atomic_discovery_admission.py`,
  `src/repositories/discovery_repository.py`, `src/schemas/artifacts.py`).
- Failed execution creates no Evidence/Discovery, and Evidence admission is fenced and atomic
  (`src/application/execution/recovery/evidence_admission_recovery.py`,
  `src/application/evidence/admission_service.py`).
- Local Discovery Synthesis projection excludes Assumptions, Tasks and existing Discoveries
  (`src/memory/session_frame.py:196-251`).

## Highest-Risk Gaps

1. Commit authorization is not uniformly tied to a durable approved proposal outside the covered
   Task, decomposition, Objective, execution, and Discovery paths.
2. Planner authors the operational contract and no concrete Data Explorer exists.
3. The composition root requires a trusted `AuthenticatedPrincipalResolver`, but no deployment
   authentication implementation is checked in.
4. Validity propagation has no production authority-issuance workflow and its explicit upgrade
   path/immutability triggers support SQLite only.
5. Package 1 now keeps a technically failed Hypothesis in `testing`, admits an exact-contract retry,
   and durably consumes repeated-failure inboxes. Changed-contract successor creation remains
   intentionally outside Package 1.

Wave 0.1 removes the raw-dataset builtin from the Hypothesis Analyst scaffold. Wave 1.1A adds Data
Explorer output, protected synthesis input, and Hypothesis Analyst result contracts. Wave 1.1B-1
rewires the executor-facing runtime to `DataExplorerResult` through one private application bridge
without migrating the durable receiver payload. It does not implement either specialist or remove
application-authored scientific synthesis.

Wave 1.1B-2A introduced the observation-only admission contract. Package 1 activates it: the
production finalizer now persists deterministic AnalysisFrame and immutable Evidence records,
advances the run to `EVIDENCE_ADMITTED` and the Hypothesis to `READY_FOR_EVALUATION`, and consumes
the authoritative inbox in one fenced commit. Package 2 now performs protected Evidence evaluation
and stops at a durable `proposal_ready` or typed failure. Package 3 now verifies the exact proposal
and a durable actor-authorized decision and returns a deterministic detached
`DiscoveryAdmissionPlan`. Package 4 provides atomic validity propagation for persisted source
validity events. Package 5 durably claims, reconstructs and commits the exact Discovery chain in
one SQLite transaction, including its conclusion SessionFrame and Package 4 interaction.
Package 6 removes obsolete scientific compatibility modules, provides schema-level quarantine and
legacy migration, and wires Packages 1–5 through the fail-closed
`src/application/runtime.py` composition root. The root requires external authentication, Analyst
model and Data Explorer adapters; it supplies none by default. The persistent E2E matrix proves all
four epistemic outcomes through proposal, governance, Discovery admission, retrieval, invalidation,
and retrieval exclusion.

## Dependency Order

1. Lock the responsibility and framework contracts (completed by canonical architecture documents).
2. Add authorization/context boundary tests and versioned specialist proposal contracts
   (completed through the Package 5 authority boundary; product authentication-adapter integration
   remains).
3. Move operationalization to Hypothesis Analyst.
4. Introduce Data Explorer observation-only output and Graph Miner retrieval contract.
5. Move Evidence evaluation/Discovery proposal to Hypothesis Analyst (completed by Package 2).
6. Implement the atomic Discovery admission transaction (completed by reviewed Package 5 for the
   SQLite persistence boundary).
7. Complete Planner branches, bootstrap, DVC/cleaning, then cache.

Package-level remediation details remain in ignored local audit notes and are not part of the
clean-clone authority chain.

## Owner Decisions Required

- SQLModel relational graph abstraction versus another graph store.
- Hypothesis approval/transition semantics and changed-contract reruns.
- Minimum reproducibility envelope for Evidence admission.
- Governance policy for plan, Assumption, cleaning, conflict and SessionFrame changes.
- SessionFrame current-cardinality/scoping and legacy database migration support.
- Release-gate policy for lint, format, mypy and CI.
