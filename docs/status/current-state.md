# Current state

This page answers one question: **what is supported by the current
implementation?** It describes the M1-A source checkpoint
`2d5bb45942e34f401c6a4462601c571c260a36e3`, based on `main` commit
`d7348144b4678a83de8f08c43e9af14305bbc9be` and inspected on 2026-08-09.
A schema, table, interface, stub, fixture, or configuration entry is not a
supported workflow by itself.

The [MVP runtime subset](../architecture/mvp-runtime-subset.md) defines the
smaller executable slice. It does not replace the
[canonical architecture](../architecture/system-overview.md), whose deferred
Hypothesis, Discovery, scientific, governance, validity, and recovery
contracts remain authoritative targets.

## Capability summary

| Reader-visible capability | Status | Current boundary |
| --- | --- | --- |
| M1-A research-state contracts | **Implemented** | The active `Objective`, `Assumption`, `Task`, `DataProfile`, `Evidence`, and `SessionFrame` schemas implement the approved executable MVP subset. No parallel MVP FCO family exists. |
| Objective and Assumption | **Implemented** | `Objective` and planning-only `Assumption` each have stable UUID identity and non-empty text. M1-A implements typed state, not Planner behavior for changing either object. |
| Task lifecycle | **Implemented** | Active Task has `task_id`, non-empty `instruction`, and exactly `PENDING`, `RUNNING`, `COMPLETED`, or `FAILED`. Legacy Task taxonomy and scientific fields are not accepted by the active schema. |
| DataProfile and deterministic profiling | **Implemented** | Immutable DataProfile has `data_profile_id`, row and column counts, and ordered typed columns. Numeric non-boolean columns are `CONTINUOUS`; boolean and supported non-numeric columns are `DISCRETE`. Continuous summaries are finite descriptive statistics; discrete summaries use complete bounded counts or deterministic top-N values. Profiling is local and model-free. |
| Direct MVP Evidence | **Implemented** | Immutable Evidence retains structured JSON-safe content, artifact references, bounded producer/work/dataset/tool provenance, and real `task_id` plus `data_profile_id` lineage. Unsupported live pandas, NumPy scalar, non-finite, and arbitrary Python values fail validation. Evidence does not require Hypothesis, AnalysisFrame, or canonical ExecutionRun. |
| MVP SessionFrame | **Implemented** | The active typed container retains one optional Objective, ordered Assumptions, Tasks, Evidence, and one optional active DataProfile. It rejects duplicate IDs, orphan Evidence, Evidence without a DataProfile, and Evidence for a different profile. A failed Task does not create or require Evidence. |
| Bounded persistence | **Verified on SQLite** | Minimum Objective, Assumption, Task, DataProfile, Evidence, and SessionFrame mappings round-trip on fresh SQLite state. Task persistence mutates status only. Evidence persistence fails closed unless the referenced Task and DataProfile exist. Objective and Assumption behavioral updates are explicitly **Deferred** to M1-B. Durable restart/recovery is not claimed. |
| Executor registry and dispatch | **Implemented** | The S0 library boundary retains one typed `Capability`, explicit dependency-aware provider factories, provider reuse, typed async dispatch, fail-closed missing registration, controlled provider errors, and role-native results. |
| Data Explorer | **Partially implemented** | The bounded local provider consumes the active Task contract and can return role-native analysis observations or an M1-A DataProfile candidate from a direct capability request. It does not create or admit Evidence. Transformation remains a typed blocker until successor dataset state exists. |
| Planner behavior and `PlannerWorkOutcome` consumption | **Deferred** | The active Planner graph remains a donor scaffold. M1-B owns typed-state inspection, Task creation, capability selection, result consumption, authorized state updates, and user response behavior. |
| M3-A Data Explorer execution and Evidence integration | **Deferred** | Production bounded Python execution, full tool coverage, real Data Explorer-to-Evidence admission, and successor transformation are not implemented by M1-A. |
| M5-A runtime composition | **Deferred** | No supported Planner-to-Data Explorer-to-Evidence-to-SessionFrame user workflow is composed. |
| Canonical scientific runtime | **Deferred** | Hypothesis and Discovery remain canonical FCOs but are not dependencies of the active MVP state. Hypothesis Analyst, scientific investigation, EvidenceRequest, canonical ExecutionRun and AnalysisFrame, protected evaluation, governance, Discovery admission, and validity propagation remain M2/M3-B/M4 work. |
| Runtime entry boundary | **Unsupported** | The installed `cognieda` script is a development placeholder, not a supported product CLI, service, or complete research-state request pipeline. |
| External integrations | **Unsupported** | DVC execution, graph-database integration, external MCP composition, deployment adapters, and non-SQLite database support are not verified. |

## Active M1-A contracts

The executable research-state path is:

```text
Objective(objective_id, text)
Assumption(assumption_id, text)
Task(task_id, instruction, status)
DataProfile(data_profile_id, row_count, column_count, columns)
Evidence(evidence_id, task_id, data_profile_id, content, provenance, artifact_refs)
SessionFrame(objective, assumptions, tasks, evidences, data_profile)
```

`ColumnProfile` retains name, raw dtype, `DISCRETE` or `CONTINUOUS` variable
type, distinct count, missing count, and a matching typed summary. The active
schemas reject the donor fields removed by the hard cutover; those fields are
not compatibility fallbacks.

Direct Task-to-Evidence linkage is the MVP executable-subset contract. Full
scientific Evidence lineage remains **Deferred** to M2/M3-B. The implementation
does not fabricate a Hypothesis, use `hypothesis_id = task_id`, or create fake
AnalysisFrame or ExecutionRun references.

## Deferred donor isolation

Canonical-heavy donor modules for Planner operations, scientific execution
attempts, Hypothesis persistence, Discovery retrieval, and old context
projections are not active M1-A workflows. Their legacy tests remain present
but are explicitly skipped where the hard cutover invalidated their executable
assumptions. This preserves the design evidence without polluting active MVP
schemas with compatibility fields.

The registered Data Explorer and S0 dispatcher were migrated. The unregistered
Hypothesis Analyst scaffold, legacy context builder, Planner operation schemas,
and scientific repositories may still mention canonical or donor fields; they
are **Deferred**, are not composed into the MVP runtime, and must not be treated
as supported consumers of the M1-A schemas.

## Verification qualification

At the M1-A source checkpoint:

- the dedicated schema suite recorded **34 passes**;
- the executor suite recorded **18 passes**;
- bounded SQLite repository and fail-closed lineage checks recorded **5 passes**;
- the broad suite excluding exactly three pre-existing Planner collection
  modules recorded **82 passes and 72 explicit skips**.

Full collection still stops on the three baseline Planner donor mismatches:

- `tests/agents/planner/test_request_understanding.py` imports
  `TaskManagementDraft`, `route_intent`, and `understand_request`;
- `tests/agents/planner/test_task_decomposition.py` imports
  `ChildTaskProposalDraft`;
- `tests/repositories/test_planner_operations.py` imports `manage_tasks`.

The corresponding Planner source defines none of those symbols. This is
pre-existing M1-B debt, not an M1-A research-state regression.

## Design target: dependency inversion

The target architecture keeps core agents dependent on protocols, bootstrap
responsible for concrete composition, and external adapters outside core
agents. S0 establishes the bounded dispatcher foundation. The final package
placement and broader adapter refactor remain a **Design target** beyond M1-A.
