# Scientific Specialist Contracts

> **Authority:** canonical target contract, subordinate to `AGENTS.md` and
> [Agent Responsibility Boundaries](agent-responsibility-boundaries.md).
> **Implementation status:** schema foundation, executor-facing result migration,
> protected Hypothesis Analyst evaluation, governance, atomic Discovery admission, and
> validity propagation are implemented for the local SQLite runtime.

These contracts establish one typed boundary between application-owned attempt identity, Data
Explorer observation, protected Hypothesis Analyst evaluation, and a lifecycle-distinct Discovery
proposal. They are ordinary Pydantic models suitable for later PydanticAI structured output. They
do not contain PydanticAI, LangGraph, SQLModel, repository, or application-service types.

## Contract Ownership

| Boundary | Accountable owner | Carries | Must not carry |
| --- | --- | --- | --- |
| Durable attempt envelope | Application services | ExecutionRun ID, dispatch key, lease epoch, Task/Hypothesis/DataProfile identity, receipt fencing and idempotency | Specialist-authored scientific wording |
| `DataExplorerResult` | Data Explorer | AnalysisFrame and Evidence observations, sample/exclusion/missingness facts, technical limitations and bounded diagnostics | Discovery, evaluation, finalization, lifecycle mutation, durable attempt identity |
| `DiscoverySynthesisBundle` | Application protected-context assembler | Immutable evaluation snapshots, active admitted Evidence, approved scientific contract, execution/validity inputs and bundle digest | Planning roles, prior conclusions, raw chat, caches, pending work or generic bags |
| `HypothesisAnalystResult` | Hypothesis Analyst | `DiscoveryProposal` or typed `EvaluationFailure` | Persistence, approval, durable Discovery identity or lifecycle mutation |
| Commit/repositories | Deterministic application/domain layer | Lineage, lifecycle, cardinality and atomic persistence | Unvalidated specialist output |

## Canonical Schema Placement

`src/schemas/execution/observations.py` owns `AnalysisFrameObservation` and
`EvidenceObservation`. `src/schemas/execution/data_explorer.py` owns the Data Explorer result
models, and `src/schemas/execution/contracts.py` owns the prepared/receipt transport contracts.
Neither `schemas.evaluation` nor Planner types re-export these execution schemas.

`src/schemas/evaluation/` owns all lifecycle-distinct evaluation specialist models. Its evaluation
snapshots intentionally omit mutable persistence state that is not scientific input:

- `HypothesisEvaluationSnapshot` omits Task identity, Hypothesis lifecycle status and timestamps,
  while retaining the approved claim, scope, variables, method, parameters, decision rule,
  evidence expectation and uncertainty requirements.
- `DataProfileEvaluationSnapshot` contains only accepted dataset-version metadata required for
  evaluation; it cannot represent an unaccepted profile.
- `AnalysisFrameEvaluationSnapshot` contains immutable frame identity and view provenance without
  copying a mutable persistence record.
- `AdmittedEvidenceSnapshot` copies only active observed content and exact provenance needed for
  evaluation; it omits timestamps, artifacts, lifecycle mutation, and unrelated persistence state.

These are evaluation-specific snapshots, not aliases for persisted FCOs and not new FCOs.

## Data Explorer Output

`DataExplorerResult` is discriminated by `status`:

- `DataExplorerSuccessResult(status="success")` requires one `AnalysisFrameObservation`, one
  `EvidenceObservation`, typed `ExecutionDetails`, and optional bounded `TechnicalDiagnostic`
  entries.
- `DataExplorerFailureResult(status="failed")` requires a `DataExplorerFailureReason`, message,
  typed diagnostic retry disposition, limitations, diagnostics and artifact/log references. The
  retry disposition is diagnostic only; the application service retains retry authority.

Method, parameters, code/environment references, artifacts and analytical limitations live once
inside `EvidenceObservation`. Seed, sample sizes, exclusions, missing-data policy and technical
limitations live once inside `ExecutionDetails`. The success contract has no parameter hash or
other attempt-envelope mirror.

All models reject unknown fields, including nested observation and detail models. This prevents a
caller from hiding `finalize`, evaluation, Discovery wording, lifecycle mutation or identity fields
inside a nested payload.

## Protected Evaluation Input

`DiscoverySynthesisBundle` is frozen and versioned. It requires:

- one `HypothesisEvaluationSnapshot` of the durably approved scientific contract;
- one accepted `DataProfileEvaluationSnapshot`;
- one or more `AnalysisFrameEvaluationSnapshot` values;
- one or more active admitted `Evidence` records;
- typed execution details, explicit validity requirements, and an application-supplied input
  digest.

Cross-field validators require matching DataProfile, Hypothesis, AnalysisFrame, method and
parameter lineage, unique Evidence IDs, and active Evidence lifecycle. Method, parameters,
decision rule, scope and uncertainty requirements come from the approved Hypothesis snapshot;
observed result, code/environment/artifact provenance and analytical limitations come from
Evidence; frame and sample/reproducibility facts remain separate typed inputs.

The bundle has no field capable of carrying an Assumption, Task, existing Discovery, SessionFrame,
UserDecision, GeneratedView, PlannerOperation, raw chat, pending/open work, stale/dead-end context,
cache summary, unverified summary, or generic `context`/`metadata`/`payload`/`extensions` bag.

## Hypothesis Analyst Output

`HypothesisAnalystResult` is discriminated by `status`:

- `DiscoveryProposal(status="proposed")` covers supported, contradicted, inconclusive and
  insufficient-evidence outcomes. It reuses `DiscoveryClaim`, `DiscoveryEpistemicStatus`, and
  `ValidityBasis`. It uses canonical `evidence_ids` rather than a renamed mirror and requires scope,
  Evidence and validity-basis alignment plus explicit evidence strength.
- `EvaluationFailure(status="failed")` covers inadmissible Evidence, invalid lineage, scope
  mismatch, missing mandatory provenance, unsupported contract version and evaluation that is not
  identifiable.

Inconclusive and insufficient-evidence outcomes remain evidence-bound proposals, not failures.
`DiscoveryProposal` has no durable Discovery ID, commit/finalize instruction, approval state,
PlannerOperation, repository handle, or Task/Hypothesis lifecycle field.

## Durable Identity Ownership

The following remain exclusively application/envelope-owned and are absent from specialist
outputs:

- `execution_run_id`
- `dispatch_idempotency_key`
- `lease_epoch`
- `task_id`
- `hypothesis_id`
- `data_profile_id`
- `parameter_hash`

Scientifically required lineage IDs appear only in protected input snapshots, admitted Evidence,
or `ValidityBasis`; they are not returned as a second authority by Data Explorer or Hypothesis
Analyst.

## Removed Legacy Mixed `ExecutorResult`

The former mixed contract is absent from active source. The table records the historical field
split that produced the current separate specialist and application contracts; it is not a
supported compatibility surface.

| Historical field | Classification | Current disposition |
| --- | --- | --- |
| `status` | Application diagnostic plus obsolete mixed discriminator | Application attempt state and separate specialist discriminators |
| `analysis_frame` | Data Explorer observation | Canonical `AnalysisFrameObservation` reused by `DataExplorerSuccessResult` |
| `execution_run` | Durable transport identity/diagnostic mirror | Application envelope only; absent from specialist output |
| `evidence_observation` | Data Explorer observation | Canonical `EvidenceObservation` reused by `DataExplorerSuccessResult` |
| `evaluation.outcome` | Hypothesis Analyst evaluation | `DiscoveryProposal.epistemic_status` and structured claim/validity basis |
| `evaluation.note` | Hypothesis Analyst scientific wording/uncertainty | Structured `DiscoveryClaim` and `ValidityBasis.uncertainty` |
| `evaluation.finalize` | Obsolete scientific authority | Removed; deterministic application workflow governs admission/commit |
| `error_message` | Application diagnostic | Typed Data Explorer failure plus application attempt diagnostics |

No compatibility adapter or runtime consumer retains the mixed contract.

## Current Implementation Status

Implemented through Package 6:

- `DataExplorerResult` is now the canonical executor-facing runtime output boundary (`src/agents/executor/`).
- Executor-facing contracts no longer import, produce, or expose legacy mixed `ExecutorResult` or scientific evaluation/finalization fields.
- Durable attempt identities (`execution_run_id`, `task_id`, `hypothesis_id`, `data_profile_id`, `dispatch_idempotency_key`, `lease_epoch`) are bound exclusively by durable application state.
- The durable receiver accepts the same canonical `DataExplorerResult`; no mirror DTO or compatibility bridge remains.
- The Data Explorer dispatcher resolves only the exact executor id explicitly registered by its
  runtime. Graph Miner and Hypothesis Analyst have no registry entry, dispatcher input, or
  compatibility executor alias.
- The unused `PlannerState.executor_result` mixed-result field and Planner `ExecutorResult` re-export were removed; no active Planner route reads legacy scientific advice.
- Hypothesis Analyst consumes only the protected bundle and is the sole source of the exact
  `DiscoveryProposal`; atomic admission cannot rewrite that proposal.

Not yet implemented:

- A deployment-supplied Hypothesis Analyst model and concrete Data Explorer implementation.
- Post-failure Hypothesis state transition redesign.
