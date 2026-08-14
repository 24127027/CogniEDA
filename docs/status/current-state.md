# Current state

This page answers one question: **what is supported by the current
implementation?** It describes source and tests inspected on 2026-08-15 on an
implementation branch based on fetched `origin/main`
`231fb8decd767f79e17f182e20da7d6d26662fd2`. A
schema, table, interface, stub, fixture, configuration entry, or directory is
not a supported workflow by itself.

The [MVP-v2 baseline](../architecture/mvp-runtime-subset.md) defines the
minimum complete scientific research loop. It is a **Design target**, not the
current implementation. The [canonical architecture](../architecture/system-overview.md)
remains the long-term authority. This page identifies which bounded current
foundations are useful, which are transitional, and which MVP-v2 boundaries
remain **Deferred** or **Unsupported**.

## Capability summary

| Reader-visible capability | Status | Current boundary |
| --- | --- | --- |
| M1-A research-state contracts | **Implemented** | The active `Objective`, `Assumption`, `Task`, `DataProfile`, `Evidence`, and materialized `SessionFrame` schemas implement a bounded transitional foundation. They are not the complete canonical contracts required by MVP-v2, and no parallel FCO family exists. |
| Objective and Assumption | **Implemented** | Immutable `Objective` and planning-only `Assumption` each have stable UUID identity and non-empty text. Planner may return a transient candidate Plan containing the current or a newly proposed Objective, but it cannot create an Assumption. The independent `PlanAdmissionService` may atomically admit the exact Objective supplied in an authorized bundle; every Plan Assumption must already exist with exact identity and content and is never auto-created by Plan admission. The runtime does not retain or conversationally authorize that candidate. |
| Task semantic core and execution status | **Implemented** | Active Task has immutable `task_id`, required exact `objective_id`, exactly one of `DATA`, `SCIENTIFIC`, or `GRAPH`, non-empty `instruction`, and exactly `PENDING`, `RUNNING`, `COMPLETED`, or `FAILED`. A status transition produces a validated replacement Task preserving `task_id`, `objective_id`, kind, and instruction. The repository update seam changes status only. Legacy taxonomy, `SYNTHESIS` Task work, scientific operationalization, dataset locators, and plan-coordination fields are not accepted by the active schema. Only bounded `DATA` work is executable. |
| Phase 1 Plan domain and candidate validation | **Implemented** | Immutable non-FCO `Plan` and `PlanDependency` values contain the exact Objective, exact admitted Human Assumption planning basis, canonical direct `task_ids` membership, and an explicit acyclic graph. Each dependency is one canonical outgoing-adjacency group with one prerequisite and sorted unique dependents; duplicate prerequisite groups are invalid, while one dependent may appear under several prerequisites. Deterministic `sha256:` fingerprint content is exactly Objective and Assumption representations, canonical Task IDs, and canonical grouped dependencies. The side-effect-free `PlanValidator` requires exact persisted references, membership, Objective scope, canonical representation, and fingerprint without persistence, Human interaction, provider lookup, or execution selection. |
| DataProfile and deterministic profiling | **Implemented** | Immutable DataProfile has `data_profile_id`, row and column counts, and ordered typed columns. Data Explorer produces a task-free initial candidate from an explicit absolute CSV or Parquet path with the normalized path and `sha256:<hex>` digest observed from the exact loaded bytes. Application authority atomically admits the profile and its one-to-one non-FCO physical dataset binding on SQLite without activating or switching it. Exact replay is idempotent; conflicting profile, path, or digest reuse fails closed. |
| Transitional direct Evidence | **Implemented** | Immutable Evidence retains deterministic JSON-safe content, artifact references, bounded producer/work/dataset/tool provenance, and real `task_id` plus `data_profile_id` lineage. The M3-A application service admits exactly one successful Data Explorer observation only after matching the persisted `COMPLETED` Task, authoritative DataProfile and dataset binding, request path, independently observed execution path and digest, capability, role-native plan, source role, and provenance contract. Failed, blocked, mismatched, empty, or invalid work creates no Evidence. This direct Task-to-Evidence path is bounded current capability, not the canonical scientific Evidence lineage required by MVP-v2. |
| Bounded materialized SessionFrame | **Implemented** | The current M1-A value retains one optional materialized Objective, ordered read-only materialized Assumption, Task, Evidence, and Discovery collections, and one optional materialized DataProfile. Application exact-copies all six member categories into immutable Planner `PlannerContext` without filtering, ranking, or truncation. The frame rejects duplicate IDs, orphan Evidence, Evidence for any Task not exactly `COMPLETED`, Evidence without a DataProfile, and Evidence for a different profile. It has no `session_frame_id`, Objective-bound session identity, typed reference manifest, active selectors, successor lineage, purpose/mode binding, or runtime reload authority. |
| Bounded persistence | **Verified on SQLite** | Concrete models, sessions, and repositories round-trip minimum research state, immutable Plan state, and objective-scoped active Plan selection on fresh SQLite. Plan retains normalized `plans`, `plan_assumptions`, `plan_tasks`, and atomic-edge `plan_dependencies` rows; repository writes flatten grouped dependencies and reads regroup them by prerequisite. One admission transaction validates and stages an authorized new Objective, new Tasks, exact Plan, and `objective_id -> plan_id` active pointer, then commits all or rolls all back. The append-only Plan repository exposes no update or delete surface, and replacing the active pointer leaves old Plans immutable. Durable upgrade of legacy rows and restart/recovery are not claimed. |
| Conversational Plan authorization and candidate lifecycle | **Deferred** | Application does not retain, replace, discard, or admit Planner candidate state across Human turns. `PlannerContext` contains no candidate or conversation fields. Candidate retention, conversational Human authorization, and LangGraph interrupt/resume are not implemented. The independent exact-bundle admission service and objective-scoped active Plan repository remain **Verified on SQLite**. |
| Executor registry and dispatch | **Implemented** | The role-neutral `execution` package owns the single typed `Capability` definition, explicit dependency-aware provider factories, provider reuse, typed async dispatch, fail-closed missing registration, controlled provider errors, and role-native results. Runtime provider registration is not Plan content. Specialist roles are peer packages under `agents`; Planner is not registered or represented as a Task executor, and no compatibility `agents.executor` path remains. |
| Data Explorer | **Implemented** | At the bounded M3-A library surface, execution-internal capability plumbing can invoke Data Explorer outside Plan. Data Explorer rejects direct `SCIENTIFIC` and `GRAPH` Task dispatch. It owns typed operationalization of the DATA Task instruction plus the supplied authoritative DataProfile projection into one finite `DataAnalysisPlan`; deterministic validation and tools alone compute values. Supported operations are row count, column summary, missingness, bounded value counts, descriptive statistics, bounded group summary, and bounded Pearson or Spearman correlation. Exact column names are required. Analysis contracts live under `agents.data_explorer`, not role-neutral `execution`. Data Explorer remains persistence-free and never creates Evidence. General-purpose Python execution is **Unsupported**. Transformation remains a typed blocker. |
| Phase 2 Planner cognitive core and native conversation history | **Implemented** | Planner directly owns one typed PydanticAI Agent and invokes `plan_or_answer` exactly once per non-empty request with exact typed `PlannerDeps`. `PlannerResult` can answer, request Human clarification, propose a transient Plan plus exact Task bundle, or signal continuation of a supplied active Plan. `PlannerOutput` contains that result, only native messages generated by the current invocation, and an optional controlled error. Prior `ConversationHistory` is supplied separately as native message history and remains non-authoritative. Candidate validation fails closed on Task-bundle mismatch, unknown or changed Assumptions, and continuation without an active Plan. `PlannerContext` contains authoritative readable state only. The model-visible contracts contain no Capability or execution routing. Planner performs no persistence, admission, activation, dispatch, or Evidence admission. |
| M3-A Data Explorer execution and Evidence integration | **Implemented** | The bounded library/data-authority surface proves immutable path-plus-content DataProfile binding, Data Explorer-owned bounded planning, deterministic real tool execution, typed provenance with the actual execution digest, application-owned atomic profile/binding admission, and application-owned immutable Evidence admission. Exact replay is idempotent; wrong-path, wrong-profile, same-path mutation, planning failure, blocker, lineage mismatch, and invalid payload paths create zero Evidence. Retained runtime composition is outside this claim. |
| Multi-provider model construction | **Partially implemented** | Required provider/name/key configuration resolves workspace-first. Canonical provider identity is exactly OpenAI, Google, or Anthropic; the `gemini` input alias normalizes to Google before the generic factory dispatches. API key and optional base URL fall back first to provider-neutral environment values and then to legacy OpenAI-named values. Deterministic unit tests cover resolution and construction without external calls; no live provider call or supported multi-provider end-to-end runtime is verified. |
| Retained runtime composition | **Deferred** | No supported Planner-to-real-Data-Explorer-to-Evidence-to-SessionFrame user workflow is composed, and the current in-process frame and conversation are not restored after restart. |
| Canonical SessionFrame and durable session state | **Deferred** | The MVP-v2 target is a typed-reference research-session membership FCO with active Objective/DataProfile selectors, governed successor state, Objective-bound session ownership, deterministic context resolution, and restart reconstruction. The current materialized M1-A value does not implement that contract. |
| Canonical planning and scientific runtime | **Deferred** | Plan domain, pure validation, transient invocation-local candidate authoring, atomic exact-bundle admission, and objective-scoped active selection exist as separate bounded surfaces. Candidate lifecycle, conversational Human authorization, Planner LangGraph composition, Task DAG selection/execution, and successor/replanning orchestration remain absent, and Plan binds no exact DataProfile. The scientific runtime, canonical Evidence admission, protected evaluation, governance, Discovery admission, and validity propagation remain unsupported workflows required by MVP-v2. |
| Plan lifecycle and replanning | **Partially implemented** | Objective-scoped active selection is implemented, and successor activation does not mutate the old Plan. Candidate retention, conversational authorization, interrupt/resume, Plan completion, interruption, successor-authoring policy, and actual-cause taxonomy remain **Deferred**. Scientific stopping remains InvestigationProtocol-owned, and bounded execution stopping remains work-order-owned. |
| Semantic graph and Graph Miner | **Deferred** | Objective, Hypothesis, Evidence, and Discovery remain the exact target semantic graph membership, but no supported semantic projection or read-only Graph Miner runtime is composed. The Graph Miner package is an unregistered scaffold that raises `NotImplementedError`. |
| Runtime entry boundary | **Partially implemented** | Runtime bootstrap composes fresh-SQLite metadata, the registry, Data Explorer provider, dispatcher, Phase 2 Planner, model factory, and workspace-local agent tooling. One in-process `Application` owns the current SessionFrame and native conversation history, passes history separately from `PlannerContext`, and resolves the active Plan for the frame's exact current Objective into that authoritative projection. It does not retain or admit transient candidates. `continue_execution` remains a no-execution semantic result for an already-active Plan. Persisted state is not recovered and no Plan execution loop exists, so this is not a supported product CLI. |
| Workspace filesystem ownership | **Implemented** | `Workspace.open()` normalizes the selected user research project root. Conventional `data/`, private `.cognieda/`, `state/`, and `sessions/` paths derive from that root and remain independent of process CWD. Initialization creates `.cognieda/project.toml` and `data/`; specific data and operational subdirectories remain lazy. External absolute dataset paths remain loadable and are not forced into the Workspace. Filesystem presence does not perform DataProfile admission. |
| External integrations | **Unsupported** | DVC execution, graph-database integration, external MCP composition, deployment adapters, and non-SQLite database support are not verified. |

## Active M1-A contracts

The executable research-state path is:

```text
Objective(objective_id, text)
Assumption(assumption_id, text)
Task(task_id, objective_id, kind, instruction, status)
DataProfile(data_profile_id, row_count, column_count, columns)
Evidence(evidence_id, task_id, data_profile_id, content, provenance, artifact_refs)
Discovery(discovery_id, hypothesis_id, evidence_ids, claim, validity_basis, ...)
SessionFrame(objective, assumptions, tasks, evidences, discoveries, data_profile)
```

`ColumnProfile` retains name, raw dtype, `DISCRETE` or `CONTINUOUS` variable
type, distinct count, missing count, and a matching typed summary. The active
schemas reject the donor fields removed by the hard cutover; those fields are
not compatibility fallbacks.

Direct Task-to-Evidence linkage is a bounded transitional implementation
contract. Full scientific Evidence lineage remains **Deferred** and is
required by MVP-v2. The implementation
does not fabricate a Hypothesis, use `hypothesis_id = task_id`, or create fake
AnalysisFrame or ExecutionRun references.

## Bounded M3-A data-authority surface

`DATA_ANALYSIS` requires an explicit absolute `dataset_path`, exact
`data_profile_id`, and a `DataExplorerInput` carrying the matching authoritative
DataProfile projection.
Execution-internal callers select the capability; Phase 2 Planner has no
model-visible Capability and does not dispatch.
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

The application service does not append to `SessionFrame`; canonical
typed-reference membership, active-profile selection, retained state, and
restart reconstruction remain **Deferred**.

## Superseded donor removal and deferred isolation

The generic retrieval package, its filter/rank/truncate policy, retrieval-only
schemas and `ContextMode`, and its donor policy tests have been removed. No
replacement retrieval, ranking, embedding, or supplemental-context subsystem is
implemented. Canonical-heavy donor modules for scientific execution attempts
and Hypothesis persistence remain outside active bounded workflows.

The registered Data Explorer and S0 dispatcher retain their role boundaries at
their ownership paths. The unregistered Hypothesis Analyst scaffold, non-Task
Planner operation schemas, and scientific repositories are **Deferred**, are
not composed into the bounded runtime, and
must not be treated as supported consumers of the active schemas. The old Task
taxonomy and obsolete Task-specific PlannerOperation mutation machinery have
been removed. Canonical `TaskKind` is exactly `DATA`, `SCIENTIFIC`, and `GRAPH`;
Planner response synthesis is not Task work. The Phase 1 Plan domain and
side-effect-free candidate validation are **Implemented**, and its append-only
exact snapshot repository foundation is **Verified on SQLite**. Historical
Objective and Assumption content reconstructs from immutable Plan-owned
snapshots while referenced FCO existence still fails closed. Transient
invocation-local Planner candidate authoring is **Implemented**. Commit-boundary
validation, atomic exact-bundle persistence, and objective-scoped activation
are **Verified on SQLite** through independent application-authority services.
Candidate lifecycle, conversational authorization, LangGraph interrupt/resume,
lifecycle progression, durable recovery, and runtime execution remain
**Deferred**.

## Verification qualification

Phase 2 focused tests use a deterministic fake PydanticAI Agent boundary to
verify direct Agent ownership, exact typed dependency injection, one invocation,
native history pass-through, current-message isolation, immediate answers,
Objective reuse and proposal, exact Assumption validation, candidate Task-bundle
coherence, continuation gating, and the absence of model-visible Capability.
Runtime tests prove that candidate state remains invocation-local, Application
has no pending-candidate lifecycle fields or transition method, native history
is passed separately from `PlannerContext`, and a later continuation result
does not admit an earlier candidate. Independent service tests prove atomic
admission and rollback; runtime context tests prove that the exact
objective-scoped active Plan reaches `PlannerContext` alongside all six
materialized SessionFrame member categories. Layer tests
verify no dataset implementation or scientific-authority import, no SessionFrame
Planner dependency, and no legacy Planner model, graph, node, classifier, or
capability-selection surface.
Workspace ownership and documentation
regressions retain their existing boundaries. M3-A focused tests additionally
execute real CSV and Parquet data, all seven allowlisted operations, explicit
Workspace and external paths under an arbitrary CWD, source-file immutability,
atomic candidate/profile/binding admission, Data Explorer-owned fake-planner
operationalization, successful and replayed Evidence admission, same-path
mutation, wrong-profile/path, unsupported/invalid planning, and zero-Evidence
failure paths.

Focused verification on 2026-08-15 ran:

```text
uv run pytest -q \
  tests/agents/planner \
  tests/application/services/test_plan_admission.py \
  tests/runtime/test_planner_context.py \
  tests/runtime/test_conversation.py \
  tests/schemas/test_plan.py \
  tests/schemas/test_mvp_session_frame.py \
  tests/infrastructure/persistence/test_plan_repository.py \
  tests/architecture/test_documentation_ia.py \
  tests/architecture/test_layer_boundaries.py::test_planner_cannot_access_dataset_implementation_directly \
  tests/architecture/test_layer_boundaries.py::test_planner_cognitive_core_does_not_import_deferred_scientific_authority \
  tests/architecture/test_layer_boundaries.py::test_planner_has_no_session_frame_dependency_or_legacy_graph_surface \
  tests/architecture/test_layer_boundaries.py::test_planner_production_source_has_no_obsolete_cognitive_symbols \
  tests/architecture/test_layer_boundaries.py::test_inward_layers_do_not_depend_on_cli \
  tests/architecture/test_layer_boundaries.py::test_removed_ownership_packages_have_no_python_source \
  tests/architecture/test_layer_boundaries.py::test_specialist_roles_are_peer_packages
```

Result: **111 passed**. This is changed-boundary evidence, not a claim that the
deferred lifecycle, tool, or scientific workflows exist.

## Design target: dependency inversion

**Partially implemented.** Agents consume inward-facing dispatcher and model
factory contracts; runtime bootstrap constructs concrete execution, LLM, MCP,
skills, and workspace dependencies; dataset and persistence adapters live
under infrastructure; and CLI presentation is outside runtime core. Some
application services still use concrete SQLite persistence, and the `schemas`
package still mixes active bounded, workflow, provenance, and deferred donor
contracts. A domain-contract split remains a **Design target** and must not
create parallel FCO class families.
