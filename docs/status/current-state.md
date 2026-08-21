# Current state

This page answers one question: **what is supported by the current
implementation?** It describes source and tests inspected on 2026-08-16 after
reconciliation with fetched `origin/main` at
`acdf229a50ff6292bd0914a6a64e8d5b2c7d6c50`. A
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
| Bounded typed-state contracts | **Implemented** | The active `Objective`, `Assumption`, `Task`, `Hypothesis`, `DataProfile`, `Evidence`, and materialized `SessionFrame` schemas implement a bounded transitional foundation. Task is coordination/work identity, while the materialized research-state projection includes Hypothesis. These are not the complete canonical contracts required by MVP-v2, and no parallel FCO family exists. |
| Objective and Assumption | **Implemented** | Immutable `Objective` and planning-only `Assumption` each have stable UUID identity and non-empty text. Planner may return a transient candidate Plan containing the current or a newly proposed Objective, but it cannot create an Assumption. LangGraph may retain that exact candidate outside authoritative research state. `PlanAdmissionService` may atomically admit its exact Objective only after typed conversational authorization; every Plan Assumption must already exist with exact identity and content and is never auto-created by Plan admission. |
| Task semantic core and execution status | **Implemented** | Active Task has immutable `task_id`, required exact `objective_id`, exactly one of `DATA`, `SCIENTIFIC`, or `GRAPH`, non-empty `instruction`, and exactly `PENDING`, `RUNNING`, `COMPLETED`, or `FAILED`. A status transition produces a validated replacement Task preserving `task_id`, `objective_id`, kind, and instruction. The repository update seam changes status only. Legacy taxonomy, `SYNTHESIS` Task work, scientific operationalization, dataset locators, and plan-coordination fields are not accepted by the active schema. Only bounded `DATA` work is executable. |
| Phase 1 Plan domain and candidate validation | **Implemented** | Immutable non-FCO `Plan` and `PlanDependency` values contain the exact Objective, exact admitted Human Assumption planning basis, canonical full Task definitions, and an explicit acyclic graph. `task_ids` is derived from canonical Task order and is not separately writable. Each dependency is one canonical outgoing-adjacency group with one prerequisite and sorted unique dependents; duplicate prerequisite groups are invalid, while one dependent may appear under several prerequisites. Deterministic `sha256:` fingerprint content is exactly Objective and Assumption representations, status-free Task semantic definitions, and canonical grouped dependencies. Changing Task instruction, kind, Objective scope, membership, or dependencies changes the fingerprint; changing only Task execution status does not. The side-effect-free `PlanValidator` requires exact persisted references and Task semantics, Objective scope, canonical representation, and fingerprint without persistence, Human interaction, provider lookup, or execution selection. |
| DataProfile and deterministic profiling | **Implemented** | Immutable DataProfile has `data_profile_id`, row and column counts, and ordered typed columns. Data Explorer produces a task-free initial candidate from an explicit absolute CSV or Parquet path with the normalized path and `sha256:<hex>` digest observed from the exact loaded bytes. Application authority atomically admits the profile and its one-to-one non-FCO physical dataset binding on SQLite without activating or switching it. Exact replay is idempotent; conflicting profile, path, or digest reuse fails closed. |
| Transitional direct Evidence | **Implemented** | Immutable Evidence retains deterministic JSON-safe content, artifact references, bounded producer/work/dataset/tool provenance, and real `task_id` plus `data_profile_id` lineage. The M3-A application service admits exactly one successful Data Explorer observation only after matching the persisted `COMPLETED` Task, authoritative DataProfile and dataset binding, request path, independently observed execution path and digest, capability, role-native plan, source role, and provenance contract. Failed, blocked, mismatched, empty, or invalid work creates no Evidence. This direct Task-to-Evidence path is bounded current capability, not the canonical scientific Evidence lineage required by MVP-v2. |
| Bounded materialized SessionFrame | **Verified on SQLite** | The current M1-A value retains one optional materialized Objective, ordered read-only materialized Assumption, Hypothesis, Evidence, and Discovery collections, and one optional materialized DataProfile. `SessionFrameRepository` remains authoritative for the session's current materialized frame. The fresh-context provider reads its latest committed snapshot in an exact workspace scope; absence yields deterministic empty state. `build_planner_context` reads that repository snapshot and exact-copies all six member categories into immutable `PlannerContext` and adds the objective-scoped active Plan separately. Restart reconstruction from the same database and scope is verified. Application owns no concrete repository-backed SessionFrame facade and delegates session operations to minimal runtime logic. The active graph's transient state and the Application-owned `ConversationHistory` (composed of `ConversationTurn`s and prunable `ConversationSegment`s) are both outside `PlannerContext`. The frame rejects duplicate IDs, Evidence without a DataProfile, and Evidence for a different profile. It does not retain Tasks or own Task lifecycle. The materialized value still has no canonical `session_frame_id`, typed reference manifest, active selectors, successor lineage, or purpose/mode binding. |
| Bounded persistence | **Verified on SQLite** | Concrete models, sessions, and repositories round-trip minimum research state, self-contained immutable Plan state, scoped current SessionFrame snapshots, and objective-scoped active Plan selection. Plan retains normalized `plans`, `plan_assumptions`, `plan_tasks`, and atomic-edge `plan_dependencies` rows; repository reads reconstruct full canonical `Plan.tasks` from independently persisted Tasks and regroup dependencies by prerequisite. One admission transaction validates and stages an authorized new Objective, new Tasks, exact Plan, and `objective_id -> plan_id` active pointer, then commits all or rolls all back. Task identity collision compares status-free canonical Task semantics. The append-only Plan repository exposes no update or delete surface, and replacing the active pointer leaves old Plans immutable. A targeted SQLite migration adds explicit SessionFrame scope to legacy envelopes; broader durable runtime recovery is not claimed. |
| Conversational Plan authorization and candidate lifecycle | **Implemented** | Planner-owned in-process `PlannerState` retains one self-contained exact candidate Plan and the active thread's native model history outside `PlannerContext`; no parallel candidate or proposed Task tuple exists. Natural-language Human turns resume through the Planner-owned LangGraph interrupt state; typed Planner results retain, replace, explicitly discard, or authorize the exact candidate without keyword or regex parsing. Graph topology statically declares `START -> plan_or_answer`, `await_human -> plan_or_answer`, and `admit_candidate -> END`; only `plan_or_answer` dynamically selects Human wait, admission, or completion from its semantic result. Empty Human input is rejected before graph invocation or resume. The deterministic admission node calls `PlanAdmissionService.admit(plan)`; success clears the candidate, while failure retains the exact Plan and its embedded Tasks with a controlled error. Exact admission and objective-scoped active Plan selection are **Verified on SQLite**. Checkpoints are process-local and durable restart recovery is **Deferred**. |
| Executor registry and dispatch | **Implemented** | The role-neutral `delegation` package owns the single typed `Capability` definition, executor-declared capability metadata, explicit dependency-aware factories, resolved-executor reuse, typed async dispatch, fail-closed missing registration, controlled executor errors, and role-native results. `ExecutorRegistry.register(factory)` derives registration from the constructed executor's declared `CAPABILITIES`; no obsolete caller-supplied capability list or compatibility `execution` package remains. Runtime registration is not Plan content. Specialist roles are peer packages under `agents`; Planner is not registered or represented as a Task executor. |
| Data Explorer | **Implemented** | At the bounded M3-A library surface, delegation-internal capability plumbing can invoke Data Explorer outside Plan. Data Explorer rejects direct `SCIENTIFIC` and `GRAPH` Task dispatch. It owns typed operationalization of the DATA Task instruction plus the supplied authoritative DataProfile projection into one finite `DataAnalysisPlan`; deterministic validation and tools alone compute values. Supported operations are row count, column summary, missingness, bounded value counts, descriptive statistics, bounded group summary, and bounded Pearson or Spearman correlation. Exact column names are required. Analysis contracts live under `agents.data_explorer`, not role-neutral `delegation`. Data Explorer remains persistence-free and never creates Evidence. General-purpose Python execution is **Unsupported**. Transformation remains a typed blocker. |
| Planner cognitive core and conversation memory | **Implemented** | Planner directly owns one typed PydanticAI Agent and invokes `plan_or_answer` exactly once per graph turn with exact typed `PlannerDeps`. The latest Human text is the current user prompt. Prior messages from the active graph thread are supplied separately as native `message_history`, preserving chronology without making it authoritative; only current-run `new_messages()` are appended. `ConversationTurn` and append-only `ConversationHistory` provide a separate typed non-authoritative memory contract, but Application does not own or synchronize it and durable persistence is **Deferred**. Application materializes scoped persisted SessionFrame authority and the active Plan for each turn into `PlannerContext`, then passes it run-scoped to `Planner.handle_message(message, context=context)` and through LangGraph `context` to `plan_or_answer` via `Runtime[PlannerContext]`. Plan validates its own embedded Tasks; model/context validation fails closed on unknown or changed Assumptions. `PlannerContext` contains active Plan coordination plus readable research state, including Hypotheses and excluding generic Tasks or conversation. The model-visible contracts contain no Capability or execution routing. Planner itself performs no persistence, dispatch, Hypothesis authoring, or Evidence admission. |
| M3-A Data Explorer execution and Evidence integration | **Implemented** | The bounded library/data-authority surface proves immutable path-plus-content DataProfile binding, Data Explorer-owned bounded planning, deterministic real tool execution, typed provenance with the actual execution digest, application-owned atomic profile/binding admission, and application-owned immutable Evidence admission. Exact replay is idempotent; wrong-path, wrong-profile, same-path mutation, planning failure, blocker, lineage mismatch, and invalid payload paths create zero Evidence. Retained runtime composition is outside this claim. |
| Multi-provider model construction | **Partially implemented** | Required provider/name/key configuration resolves workspace-first. Canonical provider identity is exactly OpenAI, Google, or Anthropic; the `gemini` input alias normalizes to Google before the generic factory dispatches. API key and optional base URL fall back first to provider-neutral environment values and then to legacy OpenAI-named values. Deterministic unit tests cover resolution and construction without external calls; no live provider call or supported multi-provider end-to-end runtime is verified. |
| Retained runtime composition | **Partially implemented** | Bootstrap composes the workspace-scoped persisted SessionFrame repository and active-Plan repository into a `current_planner_context()` factory closure, which is injected into Application. Planner receives dependencies and the deterministic admission service without any context provider port. Application receives only Workspace, Planner, model factory, EventBus, and the context factory closure; on each message, Application materializes `PlannerContext` and passes it to Planner, mapping the outcome to presentation-only events. Planner owns active native-message continuity, candidate review, interrupt/resume, and exact admission routing. Materialized SessionFrame current state is restart-readable from the same database and scope; LangGraph history/candidate state and `ConversationHistory` are not durably recovered. No supported Planner-to-real-Data-Explorer-to-Evidence-to-SessionFrame workflow is composed. |
| Canonical SessionFrame and durable session state | **Deferred** | The MVP-v2 target is a typed-reference research-session membership FCO with active Objective/DataProfile selectors, governed successor state, Objective-bound session ownership, deterministic context resolution, and restart reconstruction. The current materialized M1-A value does not implement that contract. |
| Canonical planning and scientific runtime | **Partially implemented** | Plan domain, pure validation, transient candidate authoring, in-process Human review, typed authorization, atomic exact-bundle admission, and objective-scoped active selection are composed. Task DAG selection/execution and successor/replanning orchestration remain absent, and Plan binds no exact DataProfile. The scientific runtime, canonical Evidence admission, protected evaluation, governance, Discovery admission, and validity propagation remain unsupported workflows required by MVP-v2. |
| Plan lifecycle and replanning | **Partially implemented** | Candidate retain/replace/discard, natural-language authorization, interrupt/resume, atomic activation, and objective-scoped active selection are implemented; successor activation does not mutate the old Plan. Plan completion, execution interruption, successor-authoring policy, actual-cause taxonomy, and durable recovery remain **Deferred**. Scientific stopping remains InvestigationProtocol-owned, and bounded execution stopping remains work-order-owned. |
| Semantic graph and Graph Miner | **Deferred** | Objective, Hypothesis, Evidence, and Discovery remain the exact target semantic graph membership, but no supported semantic projection or read-only Graph Miner runtime is composed. The Graph Miner package is an unregistered scaffold that raises `NotImplementedError`. |
| Runtime entry boundary | **Partially implemented** | Runtime bootstrap composes SQLite metadata and session access, a workspace-scoped authoritative `SessionFrameRepository`, delegation infrastructure, a fully wired Planner, model factory, EventBus, and workspace-local agent tooling. The repository is queried by the context factory closure injected into Application, not directly by Planner; Planner owns only its LangGraph, trusted process-local typed serializer, checkpointer/thread UUID, active native history, and candidate lifecycle. `Application.submit_message()` materializes `PlannerContext`, delegates normal text and context to `Planner.handle_message()`, and maps typed turn outcomes to presentation events. `PlanProposed` carries only the self-contained Plan; EventBus stores no research state or candidate authority. Typed authorization invokes application-owned admission through the deterministic graph node; `continue_execution` for an already-active Plan returns a visible no-execution result and never dispatches. Persisted graph state is not recovered and no Plan execution loop exists, so this is not a supported product CLI. |

| Workspace filesystem ownership | **Implemented** | `Workspace.open()` normalizes the selected user research project root. Conventional `data/`, private `.cognieda/`, `state/`, and `sessions/` paths derive from that root and remain independent of process CWD. Initialization creates `.cognieda/project.toml` and `data/`; specific data and operational subdirectories remain lazy. External absolute dataset paths remain loadable and are not forced into the Workspace. Filesystem presence does not perform DataProfile admission. |
| External integrations | **Unsupported** | DVC execution, graph-database integration, external MCP composition, deployment adapters, and non-SQLite database support are not verified. |

## Active M1-A contracts

The bounded typed-state surface is below. Task is coordination/work identity;
the SessionFrame line is the materialized research-state projection:

```text
Objective(objective_id, text)
Assumption(assumption_id, text)
Task(task_id, objective_id, kind, instruction, status)
DataProfile(data_profile_id, row_count, column_count, columns)
Hypothesis(hypothesis_id, task_id, profile_id, statement, scope, ...)
Evidence(evidence_id, task_id, data_profile_id, content, provenance, artifact_refs)
Discovery(discovery_id, hypothesis_id, evidence_ids, claim, validity_basis, ...)
SessionFrame(objective, assumptions, hypotheses, evidences, discoveries, data_profile)
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
snapshots while referenced FCO existence still fails closed. Transient Planner
candidate authoring, process-local retention, natural-language Human review,
typed authorization, and LangGraph interrupt/resume are **Implemented**.
Commit-boundary validation, atomic exact-bundle persistence, and
objective-scoped activation are **Verified on SQLite** through application
authority. Plan execution, completion, successor/replanning progression, and
durable recovery remain **Deferred**.

## Verification qualification

Planner-focused tests use deterministic fake Agent and PydanticAI
`FunctionModel` boundaries to verify direct Agent ownership, exact typed
`PlannerDeps` dependency injection, one invocation per graph turn, native history
pass-through and current-message isolation, fresh current-run context,
stale-context non-replay, exact candidate validation, and absence of
model-visible Capability. Planner lifecycle tests prove exact graph-state and
non-checkpointed `PlannerRunContext` shapes, candidate retain/replace/discard,
multi-turn natural-language authorization, real SQLite admission exactly once,
controlled admission failure retention, interrupt/re-interrupt behavior, thread
isolation, fresh `PlannerContext`, and visible active-Plan deferral without
dispatch. A focused serializer regression proves plain LangGraph serialization
does not preserve nested typed Plan Tasks and that the trusted process-local
serializer does. Conversation contract tests prove non-empty native-message
turns, immutable ordered append, duplicate-ID rejection, exact flattening,
and causal truncation from a `ConversationSegment` pruning subsequent model context.
Runtime Application tests prove response, proposal, clarification, error, and
command publication without transferring lifecycle authority to EventBus or
giving Application direct persistence repository ownership. Bootstrap
tests prove Application owns the `session_id` while SessionFrame and active-Plan
repositories are scoped and Planner is wired with `PlannerDeps` and `session_id` as `thread_id`.
Independent service tests prove atomic admission and rollback; runtime context tests prove that the exact
objective-scoped active Plan reaches `PlannerContext` alongside all six
materialized SessionFrame research-state member categories. Layer tests verify
no dataset implementation or scientific-authority import, no concrete
SessionFrame repository in Planner or Application, no `PlannerContext` or duplicate
conversation history in checkpoint state, and no legacy Planner model, classifier, or
capability-selection surface.
Workspace ownership and documentation
regressions retain their existing boundaries. M3-A focused tests additionally
execute real CSV and Parquet data, all seven allowlisted operations, explicit
Workspace and external paths under an arbitrary CWD, source-file immutability,
atomic candidate/profile/binding admission, Data Explorer-owned fake-planner
operationalization, successful and replayed Evidence admission, same-path
mutation, wrong-profile/path, unsupported/invalid planning, and zero-Evidence
failure paths.

Focused verification on 2026-08-16 ran:

```text
uv run pytest -q \
  tests/schemas/test_plan.py tests/agents/planner \
  tests/application/services/test_plan_admission.py \
  tests/application/services/test_plan_validation.py \
  tests/infrastructure/persistence/test_mvp_state_repositories.py \
  tests/infrastructure/persistence/test_plan_repository.py \
  tests/runtime/test_planner_context.py \
  tests/runtime/test_conversation.py \
  tests/runtime/test_application.py \
  tests/runtime/test_bootstrap.py \
  tests/cli/test_renderer.py \
  tests/architecture/test_documentation_ia.py \
  tests/architecture/test_layer_boundaries.py \
  -k "not production_source_contains_only_python_files"
```

Result: **149 passed, 1 deselected**. Changed-boundary Ruff, mypy, `compileall`,
documentation links, and obsolete-contract/routing searches also pass. The one
deselected architecture guard scans the local source tree for non-Python files;
the checkout contains an ignored provisional SQLite artifact. This is bounded
evidence, not a claim that deferred Plan execution, durable Planner lifecycle
recovery, or scientific workflows exist.

## Design target: dependency inversion

**Partially implemented.** Agents consume inward-facing dispatcher and model
factory contracts; runtime bootstrap constructs concrete execution, LLM, MCP,
skills, and workspace dependencies; dataset and persistence adapters live
under infrastructure; and CLI presentation is outside runtime core. Some
application services still use concrete SQLite persistence, and the `schemas`
package still mixes active bounded, workflow, provenance, and deferred donor
contracts. A domain-contract split remains a **Design target** and must not
create parallel FCO class families.
