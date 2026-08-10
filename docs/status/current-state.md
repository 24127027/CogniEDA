# Current state

This page answers one question: **what is supported by the current
implementation?** It describes source and tests inspected on 2026-08-10. A
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
| Objective and Assumption | **Implemented** | `Objective` and planning-only `Assumption` each have stable UUID identity and non-empty text. Bounded Planner behavior persists a new authoritative object through the narrow application mutation port, then returns a successor frame containing its ID. Semantic Objective refinement allocates a new identity; in-place Objective and Assumption repository updates remain deferred. |
| Task lifecycle | **Implemented** | Active Task has immutable `task_id` and non-empty `instruction`, plus exactly `PENDING`, `RUNNING`, `COMPLETED`, or `FAILED`. SQLite-backed status update retains Task identity and instruction; a later `PlanningContext` build resolves the current status while `SessionFrame.task_ids` remains unchanged. Legacy Task taxonomy and scientific fields are not accepted by the active schema. |
| DataProfile and deterministic profiling | **Implemented** | Immutable DataProfile has `data_profile_id`, row and column counts, and ordered typed columns. Data Explorer produces a task-free initial candidate from an explicit absolute CSV or Parquet path with the normalized path and `sha256:<hex>` digest observed from the exact loaded bytes. Application authority atomically admits the profile and its one-to-one non-FCO physical dataset binding on SQLite without activating or switching it. Exact replay is idempotent; conflicting profile, path, or digest reuse fails closed. |
| Direct MVP Evidence | **Implemented** | Immutable Evidence retains deterministic JSON-safe content, artifact references, bounded producer/work/dataset/tool provenance, and real `task_id` plus `data_profile_id` lineage. The M3-A application service admits exactly one successful Data Explorer observation only after matching the persisted `COMPLETED` Task, authoritative DataProfile and dataset binding, request path, independently observed execution path and digest, capability, role-native plan, source role, and provenance contract. Failed, blocked, mismatched, empty, or invalid work creates no Evidence. Evidence does not require Hypothesis, AnalysisFrame, or canonical ExecutionRun. |
| MVP SessionFrame | **Implemented** | The frozen schema stores cumulative ordered `objective_ids`, `assumption_ids`, `task_ids`, `data_profile_ids`, and `evidence_ids` plus active Objective and DataProfile selectors. Active IDs must be historical members and duplicates fail validation. Runtime applies a bounded pure selection policy before the runtime `PlannerContextPreparer` resolves selected refs through the concrete SQLite gateway and expands required Evidence Task/DataProfile dependencies without mutating frame membership. Historical Evidence for another DataProfile remains retained but is omitted from an active-profile run. |
| Runtime Session and conversation continuity | **Implemented** | At the in-process `Application` boundary, one immutable successor `Session` owns `SessionFrame` and complete `ConversationHistory` separately. Each `ConversationTurn` contains only `turn_id` and an ordered non-empty tuple of native PydanticAI `ModelMessage` values; there is no segment wrapper or duplicated Human/Planner surface state. Exact native tool, return, retry, structured-output, and internal traffic round-trips without CogniEDA revalidating PydanticAI's protocol. Deterministic commands use application-created `ModelRequest(UserPromptPart(...))` and `ModelResponse(TextPart(...))` values with origin metadata and no provider identity. An external deterministic Unicode-aware policy returns the four most recent complete turns plus at most four most recent older lexical matches, chronologically; omission does not delete history. Selected turns become bounded effective `message_history` after historical run instructions are cleared from the derived copy. Current authoritative `PlanningContext` is supplied through new run-scoped instructions. Empirical answer input excludes conversation, Assumptions, and native model messages. |
| Bounded persistence | **Verified on SQLite** | Concrete models, sessions, migrations, and repositories under `infrastructure.persistence` round-trip minimum Objective, Assumption, Task, DataProfile, Evidence, and ID-only SessionFrame state on fresh SQLite. Runtime bootstrap binds the concrete research-state gateway to `<workspace>/.cognieda/state/cognieda.sqlite3`; that gateway supplies runtime context reads and implements Planner's narrow mutation/lifecycle port. Task persistence changes status only. M3-A stages one Evidence insert after all admission checks and commits it once; deterministic identity makes exact replay return the existing Evidence and conflicting reuse of a work reference fail closed. SessionFrame runtime successors are still process-local and are not automatically persisted for restart. |
| Executor registry and dispatch | **Implemented** | The role-neutral `execution` package retains one typed `Capability`, explicit dependency-aware provider factories, provider reuse, typed async dispatch, fail-closed missing registration, controlled provider errors, and role-native results. Specialist roles are peer packages under `agents`; no compatibility `agents.executor` path remains. |
| Data Explorer | **Implemented** | At the bounded M3-A library surface, Planner selects `DATA_ANALYSIS` and creates only the Task and capability. Data Explorer owns typed operationalization of the Task instruction plus the supplied authoritative DataProfile projection into one finite `DataAnalysisPlan`; deterministic validation and tools alone compute values. Supported operations are row count, column summary, missingness, bounded value counts, descriptive statistics, bounded group summary, and bounded Pearson or Spearman correlation. Exact column names are required. Analysis contracts live under `agents.data_explorer`, not role-neutral `execution`. Data Explorer remains persistence-free and never creates Evidence. General-purpose Python execution is **Unsupported**. Transformation remains a typed blocker. |
| Planner behavior and `PlannerWorkOutcome` consumption | **Implemented** | Before the bounded four-node graph runs, runtime/application selects complete conversation turns and research references, derives safe effective native history, and materializes an ephemeral `PlanningContext` through the concrete runtime gateway. `Planner.run` consumes that prepared context and effective messages rather than the durable `ConversationHistory` aggregate, a context builder, or research-state read methods. The long-lived in-process Planner remains attached to the active runtime Session, but durable research objects remain authoritative outside the Planner object. The graph performs typed request understanding, persists Objective/Assumption/Task objects through `PlannerStateMutationPort` before retaining their IDs, updates only its run-local context from returned authoritative objects, selects typed capabilities, invokes the dispatcher, identity-checks outcomes, updates authoritative Task lifecycle, and composes controlled responses. `STATE_SUMMARY` labels counts from cumulative `SessionFrame` history rather than the bounded run projection. Planner still does not admit Evidence; empirical follow-up remains Evidence-only. When the bounded candidate window materializes no eligible Evidence, the response states absence only from the current bounded context rather than all session history. |
| M3-A Data Explorer execution and Evidence integration | **Implemented** | The bounded library/data-authority surface proves immutable path-plus-content DataProfile binding, Data Explorer-owned bounded planning, deterministic real tool execution, typed provenance with the actual execution digest, application-owned atomic profile/binding admission, and application-owned immutable Evidence admission. Exact replay is idempotent; wrong-path, wrong-profile, same-path mutation, planning failure, blocker, lineage mismatch, and invalid payload paths create zero Evidence. Retained runtime composition is outside this claim. |
| M5-A runtime composition | **Partially implemented** | In-process SessionFrame and Human-to-Planner conversation continuity are retained across `submit_message()` calls. The runtime still does not compose authoritative dataset execution context, M3-A Evidence admission, profile activation from admitted data, or restart-safe recovery into the user workflow. |
| Canonical scientific runtime | **Deferred** | Hypothesis and Discovery remain canonical FCOs but are not dependencies of the active MVP state. Hypothesis Analyst, scientific investigation, EvidenceRequest, canonical ExecutionRun and AnalysisFrame, protected evaluation, governance, Discovery admission, and validity propagation remain M2/M3-B/M4 work. |
| Runtime entry boundary | **Partially implemented** | An editable uv tool installation exposes `cognieda [PATH]`; `python -m cognieda` delegates to the same package entrypoint. Help parsing is bootstrap-free. Runtime bootstrap composes the registry, Data Explorer provider, dispatcher, M1-B Planner, model factory, workspace-local agent tooling, workspace-local SQLite research-object authority, and one retained in-process Session. The development REPL retains successor ID-only `SessionFrame` and native conversation state across turns, but it does not supply composed authoritative dataset execution context, automatically persist Session successors, or provide restart-safe recovery, so it is not complete M5-A or a supported product CLI. |
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
SessionFrame(objective_ids, active_objective_id, assumption_ids, task_ids,
             data_profile_ids, active_data_profile_id, evidence_ids)
```

`ColumnProfile` retains name, raw dtype, `DISCRETE` or `CONTINUOUS` variable
type, distinct count, missing count, and a matching typed summary. The active
schemas reject the donor fields removed by the hard cutover; those fields are
not compatibility fallbacks.

Direct Task-to-Evidence linkage is the MVP executable-subset contract. Full
scientific Evidence lineage remains **Deferred** to M2/M3-B. The implementation
does not fabricate a Hypothesis, use `hypothesis_id = task_id`, or create fake
AnalysisFrame or ExecutionRun references.

## Bounded M3-A data-authority surface

`DATA_ANALYSIS` requires an explicit absolute `dataset_path`, exact
`data_profile_id`, and a `DataExplorerInput` carrying the matching authoritative
DataProfile projection.
Planner selects the capability but does not construct analytical semantics.
Data Explorer passes the Task instruction, DataProfile/schema, and finite
operation set through its typed planning port, validates the returned
role-native `DataAnalysisPlan`, and invokes the deterministic tool. Runtime and
generic execution contracts do not construct the plan. `DATA_PROFILING` may
omit `data_profile_id` only when producing a non-authoritative candidate.
Dataset selection never falls back to process CWD, the product repository, or
`COGNIEDA_DE_DATASET_PATH`.

Candidate profiling reads the physical bytes once, computes SHA-256 as
`sha256:<64 lowercase hexadecimal characters>`, and parses those same bytes.
Admission persists `data_profile_id`, normalized dataset reference, and digest
as an immutable one-to-one non-FCO binding in the same transaction as a new
DataProfile. A raw repository-created DataProfile without this binding is not
M3-A Evidence-eligible. Path and digest are both authoritative: identical bytes
at another path require a new explicit profile admission, and no relocation
mechanism is implemented.

Successful analysis returns one `DataExplorerResult` with a real `work_id`,
the requested Task and capability identity, one structured observation, and
`DataExecutionProvenance` containing the normalized physical dataset path,
independently observed content digest, DataProfile identity, deterministic
tool/version/operation reference, and bounded parameters. Application admission
checks request path, observed path, observed digest, and provenance profile ID
against the authoritative binding before it creates Evidence content exactly as:

```text
{
  "operation": <validated operation>,
  "parameters": <validated bounded parameters>,
  "result": <deterministic tool output>
}
```

The application service does not append to `SessionFrame`; that coordination,
active-profile selection, and retained state remain **Deferred** to M5-A.

## Deferred donor isolation

Canonical-heavy donor modules for Planner operations, scientific execution
attempts, Hypothesis persistence, and Discovery retrieval are not active MVP
workflows. Relevant scientific and canonical-planning donor tests remain
explicitly skipped where the hard cutover invalidated their executable
assumptions. The stale pre-M1-B `create_plan` context implementation remains
removed; the current selector chooses a bounded cumulative SessionFrame subset
before the application `PlannerContextPreparer` resolves authoritative objects
and required Evidence dependencies for the four-node graph.

The registered Data Explorer and S0 dispatcher retain their role boundaries at
their ownership paths. The unregistered Hypothesis Analyst scaffold, Planner
operation schemas, deferred retrieval engine, and scientific repositories may
still mention canonical or donor fields; they are **Deferred**, are not
composed into the MVP runtime, and must not be treated as supported consumers
of the M1-A schemas.

## Verification qualification

M1-B focused tests use deterministic fake model and dispatcher boundaries to
verify typed-state inspection, natural-language and explicit action parity,
Objective and Assumption successors, bounded Task construction, all three data
capabilities, successful and failed lifecycle transitions, blocked
transformation, Task/outcome mismatch rejection, Evidence-free execution,
Evidence-grounded follow-up, and Assumption quarantine. Full pytest collection
includes the rewritten Planner modules; the former three donor import blockers
are removed. Layer tests verify that Planner cannot import pandas, dataset
loaders, Data Explorer implementations, or deferred scientific and
PlanRevision contracts directly. Workspace ownership and documentation
regressions retain their existing boundaries. M3-A focused tests additionally
execute real CSV and Parquet data, all seven allowlisted operations, explicit
Workspace and external paths under an arbitrary CWD, source-file immutability,
atomic candidate/profile/binding admission, Data Explorer-owned fake-planner
operationalization, successful and replayed Evidence admission, same-path
mutation, wrong-profile/path, unsupported/invalid planning, and zero-Evidence
failure paths.

## Design target: dependency inversion

**Partially implemented.** Agents consume inward-facing dispatcher and model
factory contracts; runtime bootstrap constructs concrete execution, LLM, MCP,
skills, and workspace dependencies; dataset and persistence adapters live
under infrastructure; and CLI presentation is outside runtime core. Some
application services still use concrete SQLite persistence, and the `schemas`
package still mixes active MVP, workflow, provenance, and deferred donor
contracts. A domain-contract split remains a **Design target** and must not
create parallel FCO class families.
