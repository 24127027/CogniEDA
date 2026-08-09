# Current state

This page answers one question: **what is supported by the current
implementation?** It describes source and tests inspected on 2026-08-09. A
schema, table, interface, stub, fixture, configuration entry, or directory is
not a supported workflow by itself.

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
| Task lifecycle | **Implemented** | Active Task has immutable `task_id` and non-empty `instruction`, plus exactly `PENDING`, `RUNNING`, `COMPLETED`, or `FAILED`. A status transition produces a validated replacement Task with the same identity and instruction. Legacy Task taxonomy and scientific fields are not accepted by the active schema. |
| DataProfile and deterministic profiling | **Implemented** | Immutable DataProfile has `data_profile_id`, row and column counts, and ordered typed columns. The Data Explorer-owned profiling boundary describes the active frame without removing duplicate rows, all-null rows, or missing values and does not mutate its input. Numeric non-boolean columns are `CONTINUOUS`; boolean and supported non-numeric columns are `DISCRETE`. Non-finite observations remain in source-shape counts but are excluded from finite descriptive calculations. Profiling is local and model-free. |
| Direct MVP Evidence | **Implemented** | Immutable Evidence retains structured JSON-safe content, artifact references, bounded producer/work/dataset/tool provenance, and real `task_id` plus `data_profile_id` lineage. Unsupported live pandas, NumPy scalar, non-finite, and arbitrary Python values fail validation. Evidence does not require Hypothesis, AnalysisFrame, or canonical ExecutionRun. |
| MVP SessionFrame | **Implemented** | The frozen active-state envelope retains one optional Objective, ordered read-only Assumption, Task, and Evidence collections, and one optional active DataProfile. Controlled seams return validated successor frames. It rejects duplicate IDs, orphan Evidence, Evidence for any Task not exactly `COMPLETED`, Evidence without a DataProfile, and Evidence for a different profile. Direct collection mutation cannot bypass validation. |
| Bounded persistence | **Verified on SQLite** | Concrete models, sessions, migrations, and repositories under `infrastructure.persistence` round-trip minimum Objective, Assumption, Task, DataProfile, Evidence, and SessionFrame state on fresh SQLite. Task persistence changes status only. Evidence persistence independently fails closed unless the referenced Task is `COMPLETED` and the referenced DataProfile exists. Objective and Assumption behavioral updates are explicitly **Deferred** to M1-B. Durable restart/recovery is not claimed. |
| Executor registry and dispatch | **Implemented** | The role-neutral `execution` package retains one typed `Capability`, explicit dependency-aware provider factories, provider reuse, typed async dispatch, fail-closed missing registration, controlled provider errors, and role-native results. Specialist roles are peer packages under `agents`; no compatibility `agents.executor` path remains. |
| Data Explorer | **Partially implemented** | The bounded local provider consumes the active Task contract and can return role-native analysis observations or an M1-A DataProfile candidate from a direct capability request. Dataset loading is an infrastructure adapter; analysis and profiling operations remain Data Explorer-owned. The raw Python analysis donor is not a production sandbox. Data Explorer does not create or admit Evidence. Transformation remains a typed blocker until successor dataset state exists. |
| Planner behavior and `PlannerWorkOutcome` consumption | **Deferred** | The active Planner graph remains a donor scaffold. M1-B owns typed-state inspection, Task creation, capability selection, result consumption, authorized state updates, and user response behavior. |
| M3-A Data Explorer execution and Evidence integration | **Deferred** | Production bounded Python execution, full tool coverage, real Data Explorer-to-Evidence admission, and successor transformation are not implemented by M1-A. |
| M5-A runtime composition | **Deferred** | No supported Planner-to-Data Explorer-to-Evidence-to-SessionFrame user workflow is composed. |
| Canonical scientific runtime | **Deferred** | Hypothesis and Discovery remain canonical FCOs but are not dependencies of the active MVP state. Hypothesis Analyst, scientific investigation, EvidenceRequest, canonical ExecutionRun and AnalysisFrame, protected evaluation, governance, Discovery admission, and validity propagation remain M2/M3-B/M4 work. |
| Runtime entry boundary | **Partially implemented** | An editable uv tool installation exposes `cognieda [PATH]`; `python -m cognieda` delegates to the same package entrypoint. Help parsing is bootstrap-free. Runtime bootstrap explicitly composes the registry, Data Explorer provider, dispatcher, Planner dependencies, model factory, and workspace-local agent tooling. Model name, base URL, and API key resolve workspace-first with environment fallback. The command reaches the development Planner REPL, not a supported product CLI, service, or complete research-state request pipeline. |
| Workspace filesystem ownership | **Implemented** | `Workspace.open()` normalizes the selected user research project root. Conventional `data/`, private `.cognieda/`, `state/`, and `sessions/` paths derive from that root and remain independent of process CWD. Initialization creates `.cognieda/project.toml` and `data/`; specific data and operational subdirectories remain lazy. External absolute dataset paths remain loadable and are not forced into the Workspace. Filesystem presence does not perform DataProfile admission. |
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
attempts, Hypothesis persistence, and Discovery retrieval are not active M1-A
workflows. Relevant donor tests remain explicitly skipped where the hard
cutover invalidated their executable assumptions. The obsolete context builder
and its duplicate SessionFrame semantics were removed rather than preserved as
an apparent implementation.

The registered Data Explorer and S0 dispatcher retain their behavior at their
new ownership paths. The unregistered Hypothesis Analyst scaffold, Planner
operation schemas, deferred retrieval engine, and scientific repositories may
still mention canonical or donor fields; they are **Deferred**, are not
composed into the MVP runtime, and must not be treated as supported consumers
of the M1-A schemas.

## Verification qualification

At the PR #36 source-layer checkpoint, the broad suite excluding exactly three
pre-existing Planner collection modules recorded **136 passes and 57 explicit
skips**. Focused layer-boundary tests also verify that Planner cannot import
pandas, dataset loaders, or Data Explorer profiling implementations directly.
Documentation regressions reject compatibility-only redirect language and
verify internal Markdown links and relative anchors. Workspace ownership
regressions reject product-root `data/`, `artifacts/`, and DVC project state,
package-relative user-data lookup, and production dependency on test fixtures.

Full collection still stops on the three baseline Planner donor mismatches:

- `tests/agents/planner/test_request_understanding.py` imports
  `TaskManagementDraft`, `route_intent`, and `understand_request`;
- `tests/agents/planner/test_task_decomposition.py` imports
  `ChildTaskProposalDraft`;
- `tests/infrastructure/persistence/test_planner_operations.py` imports
  `manage_tasks`.

The corresponding Planner source defines none of those symbols. This is
pre-existing M1-B debt, not an M1-A research-state regression.

## Design target: dependency inversion

**Partially implemented.** Agents consume inward-facing dispatcher and model
factory contracts; runtime bootstrap constructs concrete execution, LLM, MCP,
skills, and workspace dependencies; dataset and persistence adapters live
under infrastructure; and CLI presentation is outside runtime core. Some
application services still use concrete SQLite persistence, and the `schemas`
package still mixes active MVP, workflow, provenance, and deferred donor
contracts. A domain-contract split remains a **Design target** and must not
create parallel FCO class families.
