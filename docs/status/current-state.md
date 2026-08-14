# Current state

This page answers one question: **what is supported by the current
implementation?** It describes source and tests inspected on 2026-08-14 on an
implementation branch rebased onto fetched `origin/main`
`a10170630212dc5e80fda90d9716a8add20f6ed4`. A
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
| Objective and Assumption | **Implemented** | `Objective` and planning-only `Assumption` each have stable UUID identity and non-empty text. A candidate `Plan` owns the exact Objective value and exact retained Human-authored Assumption basis presented for review. Planner may return an exact-Human-text testability assessment rather than authoring an Assumption FCO; Application admits only exact text assessed as genuinely untestable in the project and rejects testable claims as Assumptions. Assumptions guide planning only and never become empirical premises. |
| Task semantic core and execution status | **Implemented** | Active Task has immutable `task_id`, required exact `objective_id`, exactly one of `DATA`, `SCIENTIFIC`, or `GRAPH`, non-empty `instruction`, and exactly `PENDING`, `RUNNING`, `COMPLETED`, or `FAILED`. A status transition produces a validated replacement Task preserving `task_id`, `objective_id`, kind, and instruction. The repository update seam changes status only. Legacy taxonomy, `SYNTHESIS` Task work, scientific operationalization, dataset locators, and plan-coordination fields are not accepted by the active schema. Only bounded `DATA` work is executable. |
| Plan V1 domain contract and candidate validation | **Implemented** | Immutable non-FCO `Plan`, `PlanTaskBinding`, and `PlanDependency` values provide the exact Objective, exact canonical Human-authored Assumption basis, one binding per member Task, binding-owned non-negative tie-permitting order rank/LOW-NORMAL-HIGH priority, explicit Objective-scoped acyclic dependencies, deterministic canonical ordering, and a routing-free `sha256:` fingerprint. Tasks remain separate FCO values carried beside the Plan for exact validation and Human review. `PlanValidator` resolves and compares the exact persisted Objective, Assumptions, and Tasks, then validates membership, Objective scope, DAG structure, canonical representation, and fingerprint without persistence. Plan contains no capability, provider, specialist, worker, tool, DataProfile identity, stopping/replan policy, approval, or activation state. |
| DataProfile and deterministic profiling | **Implemented** | Immutable DataProfile has `data_profile_id`, row and column counts, and ordered typed columns. Data Explorer produces a task-free initial candidate from an explicit absolute CSV or Parquet path with the normalized path and `sha256:<hex>` digest observed from the exact loaded bytes. Application authority atomically admits the profile and its one-to-one non-FCO physical dataset binding on SQLite without activating or switching it. Exact replay is idempotent; conflicting profile, path, or digest reuse fails closed. |
| Transitional direct Evidence | **Implemented** | Immutable Evidence retains deterministic JSON-safe content, artifact references, bounded producer/work/dataset/tool provenance, and real `task_id` plus `data_profile_id` lineage. The M3-A application service admits exactly one successful Data Explorer observation only after matching the persisted `COMPLETED` Task, authoritative DataProfile and dataset binding, request path, independently observed execution path and digest, capability, role-native plan, source role, and provenance contract. Failed, blocked, mismatched, empty, or invalid work creates no Evidence. This direct Task-to-Evidence path is bounded current capability, not the canonical scientific Evidence lineage required by MVP-v2. |
| Bounded materialized SessionFrame | **Implemented** | The current M1-A value retains one optional materialized Objective, ordered read-only materialized Assumption, Task, Evidence, and Discovery collections, and one optional materialized DataProfile. Application exact-copies all six member categories into immutable Planner `PlannerContext` without filtering, ranking, or truncation. The frame rejects duplicate IDs for every retained collection and preserves Discovery through every immutable successor seam; Discovery membership does not require co-retaining its complete Hypothesis/Evidence provenance graph. Existing Evidence closure checks remain unchanged. It has no `session_frame_id`, Objective-bound session identity, typed reference manifest, active selectors, successor lineage, purpose/mode binding, or runtime reload authority. |
| Bounded persistence | **Verified on SQLite** | Concrete models, sessions, migrations, and repositories under `infrastructure.persistence` round-trip minimum Objective, Assumption, Task, DataProfile, Evidence, materialized SessionFrame including exact retained Discovery membership, and immutable Plan state on fresh SQLite. Plan uses normalized `plans`, `plan_assumptions`, `plan_task_bindings`, and `plan_dependencies` tables plus separate `active_plans` lifecycle state. `PlanAdmissionService` validates and stages the exact approved Objective, Assumptions, Tasks, Plan, and active-plan pointer in one caller-owned transaction. Rejection and requested revision write none of those authoritative objects. The append-only repository rejects same-ID replay or collision without overwrite, fails closed on stored fingerprint mismatch, and exposes no update or delete surface. Durable upgrade of legacy rows and restart/recovery are not claimed. |
| Executor registry and dispatch | **Implemented** | The role-neutral `execution` package owns the single typed `Capability` definition, explicit dependency-aware provider factories, provider reuse, typed async dispatch, fail-closed missing registration, controlled provider errors, and role-native results. Runtime provider registration is not Plan content. Specialist roles are peer packages under `agents`; Planner is not registered or represented as a Task executor, and no compatibility `agents.executor` path remains. |
| Data Explorer | **Implemented** | At the bounded M3-A library surface, execution-internal capability plumbing can invoke Data Explorer outside Plan. Data Explorer rejects direct `SCIENTIFIC` and `GRAPH` Task dispatch. It owns typed operationalization of the DATA Task instruction plus the supplied authoritative DataProfile projection into one finite `DataAnalysisPlan`; deterministic validation and tools alone compute values. Supported operations are row count, column summary, missingness, bounded value counts, descriptive statistics, bounded group summary, and bounded Pearson or Spearman correlation. Exact column names are required. Analysis contracts live under `agents.data_explorer`, not role-neutral `execution`. Data Explorer remains persistence-free and never creates Evidence. General-purpose Python execution is **Unsupported**. Transformation remains a typed blocker. |
| Planner behavior and native conversation history | **Implemented** | Planner owns one PydanticAI `Agent` and exactly two LangGraph cognitive nodes, `plan` and `execute`. A LangGraph `interrupt` presents the exact candidate Plan and separate Task bundle between them. PLAN receives executor tools disabled; after Application atomically admits and activates the exact approved bundle, EXECUTE receives only application-authorized eligible Task scope. `PlannerDeps` contains the dispatcher and model-hidden execution authority. The active model-visible `run_data_work` tool obtains the dispatcher through `RunContext`, hides internal `Capability`, and can be called zero, one, or multiple times inside one PydanticAI run. One optional-field `PlannerCognitiveResult` and one `PlannerOutput` envelope carry the current lifecycle snapshot. `messages` contains every native PydanticAI message generated across the current lifecycle, including tool calls and returns; Application appends that complete set once only after the lifecycle completes. `PlannerContext` is the sole readable context and includes non-authoritative `ConversationHistory`; no extra graph-context wrapper, global action classifier, or SessionFrame surface remains. Planner never admits Evidence or authors Discovery. |
| M3-A Data Explorer execution and Evidence integration | **Implemented** | The bounded library/data-authority surface proves immutable path-plus-content DataProfile binding, Data Explorer-owned bounded planning, deterministic real tool execution, typed provenance with the actual execution digest, application-owned atomic profile/binding admission, and application-owned immutable Evidence admission. Exact replay is idempotent; wrong-path, wrong-profile, same-path mutation, planning failure, blocker, lineage mismatch, and invalid payload paths create zero Evidence. Retained runtime composition is outside this claim. |
| Multi-provider model construction | **Partially implemented** | Required provider/name/key configuration resolves workspace-first. Canonical provider identity is exactly OpenAI, Google, or Anthropic; the `gemini` input alias normalizes to Google before the generic factory dispatches. API key and optional base URL fall back first to provider-neutral environment values and then to legacy OpenAI-named values. Deterministic unit tests cover resolution and construction without external calls; no live provider call or supported multi-provider end-to-end runtime is verified. |
| Retained runtime composition | **Deferred** | No supported Planner-to-real-Data-Explorer-to-Evidence-to-SessionFrame user workflow is composed, and the current in-process frame and conversation are not restored after restart. |
| Canonical SessionFrame and durable session state | **Deferred** | The MVP-v2 target is a typed-reference research-session membership FCO with active Objective/DataProfile selectors, governed successor state, Objective-bound session ownership, deterministic context resolution, and restart reconstruction. The current materialized M1-A value does not implement that contract. |
| Canonical planning and scientific runtime | **Partially implemented** | Planner authors transient canonical Plan/Task bundles, Human review interrupts before authority, and Application performs exact commit-boundary validation, persistence, adoption, and active-plan selection on approval. EXECUTE enforces DAG eligibility and exposes the real Data Explorer semantic tool. Plan binds no exact DataProfile. Executable `SCIENTIFIC` and `GRAPH` workflows, Hypothesis Analyst feasibility, Hypothesis admission, InvestigationPlan/Protocol, EvidenceRequest, canonical ExecutionRun/AnalysisFrame use, canonical scientific Evidence admission, protected evaluation, typed outcomes, governance, Discovery admission, and validity propagation remain **Deferred** or **Unsupported** as noted by their owners. |
| Plan lifecycle and replanning | **Partially implemented** | Candidate presentation, exact approve/reject/revise identity, atomic activation, and execute-requested return to PLAN are implemented in process. Every replacement Plan requires another Human interrupt. Plan content contains no configurable stopping-condition or replan-trigger policy. Durable recovery, typed completion/interruption records, successor lineage, and the finite taxonomy of actual reconsideration causes remain **Deferred**. |
| Semantic graph and Graph Miner | **Deferred** | Objective, Hypothesis, Evidence, and Discovery remain the exact target semantic graph membership, but no supported semantic projection or read-only Graph Miner runtime is composed. The Graph Miner package is an unregistered scaffold that raises `NotImplementedError`. |
| Runtime entry boundary | **Partially implemented** | An editable uv tool installation exposes `cognieda [PATH]`; `python -m cognieda` delegates to the same package entrypoint. Help parsing is bootstrap-free. Runtime bootstrap composes the registry, Data Explorer provider, dispatcher, M1-B Planner, model factory, and workspace-local agent tooling. One in-process `Application` is the sole active owner of the current SessionFrame: it builds Planner context, invokes Planner, applies explicit bounded results to a successor frame, and retains append-only native conversation history across REPL turns. That state is not durably persisted or recovered, and the REPL does not supply composed dataset execution context, so it is not M5-A or a supported product CLI. |
| Workspace filesystem ownership | **Implemented** | `Workspace.open()` normalizes the selected user research project root. Conventional `data/`, private `.cognieda/`, `state/`, and `sessions/` paths derive from that root and remain independent of process CWD. Optional workspace Planner guidance is read only from `.cognieda/planner.md`; absence is valid, and repository-root `AGENTS.md` is not loaded into the product Planner. Initialization creates `.cognieda/project.toml` and `data/`; specific data and operational subdirectories remain lazy. External absolute dataset paths remain loadable and are not forced into the Workspace. Filesystem presence does not perform DataProfile admission. |
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
Planner never selects this execution-internal capability. After exact Plan
approval, the semantic `run_data_work` tool may translate an authorized DATA
interaction into this plumbing while keeping the route out of the model schema.
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
Planner response synthesis is not Task work. The Plan V1 domain and
side-effect-free candidate validation are **Implemented**, and its append-only
repository foundation is **Verified on SQLite**. Planner authoring, exact Human
approval, commit-boundary validation and persistence, activation, active
selection, DATA Task eligibility, and the semantic Data Explorer tool are
**Implemented** within the bounded in-process lifecycle. Durable recovery and
scientific or graph execution remain **Deferred**.

## Verification qualification

Planner focused tests use deterministic fake and PydanticAI function models to
verify exact readable context, one cognitive result type, exact Plan/Task Human
review, atomic approval, rejection with zero authoritative writes, replacement
Plan review, exact `PlannerDeps` phase state, dynamic tool omission during PLAN,
semantic tool visibility during EXECUTE, approved membership and DAG eligibility,
controlled dispatch failure, multiple tool calls in one Agent run, and retention
of native tool-call and tool-return messages. Layer tests verify that
Planner-visible schemas have no Capability, dispatcher, provider, or executor
surface and that Planner has no SessionFrame dependency.
Workspace ownership and documentation
regressions retain their existing boundaries. M3-A focused tests additionally
execute real CSV and Parquet data, all seven allowlisted operations, explicit
Workspace and external paths under an arbitrary CWD, source-file immutability,
atomic candidate/profile/binding admission, Data Explorer-owned fake-planner
operationalization, successful and replayed Evidence admission, same-path
mutation, wrong-profile/path, unsupported/invalid planning, and zero-Evidence
failure paths.

Focused Planner ownership and instruction verification on 2026-08-14 includes:

```text
uv run pytest tests/agents/planner tests/agents/test_instruction.py \
  tests/runtime/test_planner_context.py tests/runtime/test_conversation.py \
  tests/schemas/test_mvp_session_frame.py \
  tests/infrastructure/persistence/test_mvp_state_repositories.py \
  tests/architecture/test_layer_boundaries.py tests/schemas/test_plan.py \
  tests/application/test_plan_validator.py \
  tests/infrastructure/persistence/test_plan_repository.py -q
```

These checks are rerun for the delivery branch; exact final counts belong in
the delivery report rather than this durable status page.

## Design target: dependency inversion

**Partially implemented.** Planner consumes the inward-facing model factory
contract and typed PydanticAI dependency boundary while execution/application
seams retain role-neutral dispatcher contracts; runtime bootstrap constructs
concrete execution, LLM, MCP,
skills, and workspace dependencies; dataset and persistence adapters live
under infrastructure; and CLI presentation is outside runtime core. Some
application services still use concrete SQLite persistence, and the `schemas`
package still mixes active bounded, workflow, provenance, and deferred donor
contracts. A domain-contract split remains a **Design target** and must not
create parallel FCO class families.
