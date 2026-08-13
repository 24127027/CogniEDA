# Current state

This page answers one question: **what is supported by the current
implementation?** It describes source and tests inspected on 2026-08-13 on an
implementation branch based on fetched `origin/main`
`1be9c5f1d38c20a10bf947217f2476c934333631`. A
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
| Objective and Assumption | **Implemented** | `Objective` and planning-only `Assumption` each have stable UUID identity and non-empty text. Assumption is Human-authored only: `/assumption` and natural-language retention requests cross the same typed reasonable-testability gate, retained text must be an exact Human source span, and Planner-authored or rewritten text fails closed. Planner returns the typed decision but no Assumption object; Application verifies the source span and negative testability classification, constructs the Assumption from unchanged Human text, and adds it through the successor-frame seam. A reasonably testable Human claim creates zero Assumption and returns a controlled response that scientific investigation is required but **Unsupported** by the current DATA-only runtime. Assumption remains excluded from empirical answer support and never becomes Evidence merely through SessionFrame membership. |
| Task semantic core and execution status | **Implemented** | Active Task has immutable `task_id`, required exact `objective_id`, exactly one of `DATA`, `SCIENTIFIC`, or `GRAPH`, non-empty `instruction`, and exactly `PENDING`, `RUNNING`, `COMPLETED`, or `FAILED`. A status transition produces a validated replacement Task preserving `task_id`, `objective_id`, kind, and instruction. The repository update seam changes status only. Legacy taxonomy, `SYNTHESIS` Task work, scientific operationalization, dataset locators, and plan-coordination fields are not accepted by the active schema. Only bounded `DATA` work is executable. |
| PlanRevision V1 domain contract and candidate validation | **Implemented** | Immutable non-FCO `PlanRevision`, `PlanTaskBinding`, and `PlanDependency` values provide one binding per member Task, binding-owned non-negative tie-permitting order rank/LOW-NORMAL-HIGH priority, explicit Objective-scoped acyclic dependencies, deterministic canonical ordering, and a `sha256:` fingerprint bound only to contract version, Objective identity, Task binding coordination, and dependencies. The side-effect-free application validator resolves authoritative Objective and Task records, rejects duplicate, missing, extra, or cross-Objective Tasks, non-member or cyclic edges, non-canonical representation, and fingerprint mismatch, then returns the exact canonical candidate without persistence. PlanRevision and its bindings contain no capability, provider, specialist, worker, tool, DataProfile identity, stopping/replan policy, approval, or activation state. |
| Transient plan approval and authoritative commit | **Implemented** | Planner constructs exact canonical Objective, Task, and PlanRevision objects in memory. Application retains one pending Objective, Task tuple, and PlanRevision and accepts explicit `/approve` or `/reject`; a second proposal cannot replace the pending objects. Before approval none of the proposed objects is persisted or active. Rejection discards them. Approval invokes one application-owned SQLite transaction that persists those exact identities, revalidates the PlanRevision against the persisted Tasks, creates the sole active-revision selection, and commits atomically. Injected failure rolls Objective, Tasks, revision, and selection back together. “Transient” is an authority/lifecycle state, not a separate domain-object family. Durable pending-plan persistence, restart-safe approval, approval modes, and replanning replacement are **Deferred**. |
| DataProfile and deterministic profiling | **Implemented** | Immutable DataProfile has `data_profile_id`, row and column counts, and ordered typed columns. Data Explorer produces a task-free initial candidate from an explicit absolute CSV or Parquet path with the normalized path and `sha256:<hex>` digest observed from the exact loaded bytes. Application authority atomically admits the profile and its one-to-one non-FCO physical dataset binding on SQLite without activating or switching it. Exact replay is idempotent; conflicting profile, path, or digest reuse fails closed. |
| Transitional direct Evidence | **Implemented** | Immutable Evidence retains deterministic JSON-safe content, artifact references, bounded producer/work/dataset/tool provenance, and real `task_id` plus `data_profile_id` lineage. The M3-A application service admits exactly one successful Data Explorer observation only after matching the persisted `COMPLETED` Task, authoritative DataProfile and dataset binding, request path, independently observed execution path and digest, capability, role-native plan, source role, and provenance contract. Failed, blocked, mismatched, empty, or invalid work creates no Evidence. This direct Task-to-Evidence path is bounded current capability, not the canonical scientific Evidence lineage required by MVP-v2. |
| Bounded materialized SessionFrame | **Implemented** | The current M1-A value retains one optional materialized Objective, ordered read-only materialized Assumption, Task, and Evidence collections, and one optional materialized DataProfile. Application exact-copies all five member categories into immutable Planner `PlanningContext` without filtering, ranking, or truncation, then applies explicit Planner results through controlled successor seams. The frame rejects duplicate IDs, orphan Evidence, Evidence for any Task not exactly `COMPLETED`, Evidence without a DataProfile, and Evidence for a different profile. It has no `session_frame_id`, Objective-bound session identity, typed reference manifest, active selectors, successor lineage, purpose/mode binding, or runtime reload authority. |
| Bounded persistence | **Verified on SQLite** | Concrete models, sessions, migrations, and repositories round-trip minimum Objective, Assumption, Task, DataProfile, Evidence, SessionFrame, immutable PlanRevision, and explicit active-plan state. PlanRevision binding rows store only Task identity, rank, and priority, with no execution-routing field; `active_plan_revisions` permits at most one selection per Objective. The approved-plan service commits the exact pending Objective, Tasks, revision content, and selection atomically. The append-only revision repository exposes no update or delete surface, and no application path persists an unapproved proposal. Durable upgrade of legacy rows, active-selection replacement, Objective and Assumption update composition, and restart/recovery are not claimed. |
| Executor registry and dispatch | **Implemented** | The role-neutral `execution` package owns the single typed `Capability` definition, explicit dependency-aware provider factories, provider reuse, typed async dispatch, fail-closed missing registration, controlled provider errors, and role-native results. Runtime provider registration is not PlanRevision content. Specialist roles are peer packages under `agents`; Planner is not registered or represented as a Task executor, and no compatibility `agents.executor` path remains. |
| Data Explorer | **Implemented** | At the bounded M3-A library surface, execution-internal capability plumbing can invoke Data Explorer outside PlanRevision. Data Explorer rejects direct `SCIENTIFIC` and `GRAPH` Task dispatch. It owns typed operationalization of the DATA Task instruction plus the supplied authoritative DataProfile projection into one finite `DataAnalysisPlan`; deterministic validation and tools alone compute values. Supported operations are row count, column summary, missingness, bounded value counts, descriptive statistics, bounded group summary, and bounded Pearson or Spearman correlation. Exact column names are required. Analysis contracts live under `agents.data_explorer`, not role-neutral `execution`. Data Explorer remains persistence-free and never creates Evidence. General-purpose Python execution is **Unsupported**. Transformation remains a typed blocker. |
| Planner behavior, native conversation history, and governed DATA interactions | **Implemented** | The bounded graph receives read-only `PlanningContext`, performs typed request understanding, returns standalone Objective results, gates Human-authored Assumption requests, or constructs transient canonical Objective, DATA Task, and PlanRevision objects without dispatch. After approval, Application selects an eligible Task and supplies authoritative DataProfile and physical-binding context to a separate Planner execution invocation. The same Planner role/model may call the semantic `run_data_work` tool zero, one, or multiple times and inspect each normalized outcome; the internal capability remains hidden behind that tool boundary. Application validates returned Data Explorer identities and successful provenance before persisting terminal Task status. Planner graph state and output contain no SessionFrame, Planner is not an executor, and response synthesis is not Task work. Native model-message history remains append-only and separate from research authority. Planner does not admit computed DATA output as Evidence or create executable `SCIENTIFIC` or `GRAPH` work. |
| M3-A Data Explorer execution and Evidence integration | **Implemented** | The bounded library/data-authority surface proves immutable path-plus-content DataProfile binding, Data Explorer-owned bounded planning, deterministic real tool execution, typed provenance with the actual execution digest, application-owned atomic profile/binding admission, and application-owned immutable Evidence admission. Exact replay is idempotent; wrong-path, wrong-profile, same-path mutation, planning failure, blocker, lineage mismatch, and invalid payload paths create zero Evidence. Retained runtime composition is outside this claim. |
| Multi-provider model construction | **Partially implemented** | Required provider/name/key configuration resolves workspace-first. Canonical provider identity is exactly OpenAI, Google, or Anthropic; the `gemini` input alias normalizes to Google before the generic factory dispatches. API key and optional base URL fall back first to provider-neutral environment values and then to legacy OpenAI-named values. Deterministic unit tests cover resolution and construction without external calls; no live provider call or supported multi-provider end-to-end runtime is verified. |
| Approved DATA runtime composition | **Implemented** | A verified in-process Application test spans Human request, Planner construction of one transient canonical Objective, DATA Task, and PlanRevision, explicit approval, atomic persistence and activation of the exact identities, application-owned eligibility and authoritative DataProfile/dataset-binding resolution, Planner-led semantic Data Explorer interaction against a real CSV, application-validated completion, and Planner response. Before approval and after rejection the authoritative plan tables remain empty. Direct DATA results remain non-authoritative interaction records and Evidence count remains zero. Local model-driven tests prove that one Task may make multiple governed Data Explorer calls under the same identity. The runtime also verifies deterministic `T1 -> T2` dependency progression, order/priority subordinate to prerequisites, no completed-Task rerun, and failure when no successful governed interaction exists. |
| Canonical SessionFrame and durable session state | **Deferred** | The MVP-v2 target is a typed-reference research-session membership FCO with active Objective/DataProfile selectors, governed successor state, Objective-bound session ownership, deterministic context resolution, and restart reconstruction. The current materialized M1-A value does not implement that contract. |
| Canonical planning and scientific runtime | **Partially implemented** | The DATA-only approved-plan control path now runs, including minimum dependency eligibility, but it does not implement the canonical scientific investigation. PlanRevision binds no exact DataProfile; application execution resolves the supplied authoritative profile and physical binding downstream. Executable `SCIENTIFIC` and `GRAPH` workflows, ScientificInvestigationRun, Hypothesis Analyst feasibility, Hypothesis admission, InvestigationPlan/Protocol, EvidenceRequest, canonical ExecutionRun/AnalysisFrame use, canonical Evidence admission, protected evaluation, typed outcomes, governance, Discovery admission, and validity propagation remain **Deferred** or **Unsupported** as described by their owner pages. |
| PlanRevision lifecycle and replanning | **Partially implemented** | Exact in-process Human approval, atomic first activation, and active selection are implemented for the bounded DATA slice. An Objective with an active revision rejects another approved proposal because successor/replacement semantics are **Deferred**. Durable pending approval, restart recovery, interruption, plan completion state, successor creation, and the finite typed taxonomy of actual causes requiring reconsideration remain **Deferred**. PlanRevision content still contains no stopping-condition or replan-trigger policy. |
| Semantic graph and Graph Miner | **Deferred** | Objective, Hypothesis, Evidence, and Discovery remain the exact target semantic graph membership, but no supported semantic projection or read-only Graph Miner runtime is composed. The Graph Miner package is an unregistered scaffold that raises `NotImplementedError`. |
| Runtime entry boundary | **Partially implemented** | An editable uv tool installation exposes `cognieda [PATH]`; `python -m cognieda` delegates to the same package entrypoint. Help parsing is bootstrap-free. Runtime bootstrap composes the registry, Data Explorer provider, dispatcher, Planner, model factory, workspace-local agent tooling, and a workspace-local SQLite state store unless `COGNIEDA_DB_URL` is explicit. Application retains one pending canonical Objective, Task tuple, and PlanRevision plus the materialized SessionFrame in process. The verified DATA slice requires an already-admitted active DataProfile in that frame; product dataset adoption, durable frame/pending-plan recovery, and restart-safe approval are **Deferred**, so this remains not M5-A and not a supported product CLI. |
| Workspace filesystem ownership | **Implemented** | `Workspace.open()` normalizes the selected user research project root. Conventional `data/`, private `.cognieda/`, `state/`, and `sessions/` paths derive from that root and remain independent of process CWD. Initialization creates `.cognieda/project.toml` and `data/`; specific data and operational subdirectories remain lazy. External absolute dataset paths remain loadable and are not forced into the Workspace. Filesystem presence does not perform DataProfile admission. |
| External integrations | **Unsupported** | DVC execution, graph-database integration, external MCP composition, deployment adapters, and non-SQLite database support are not verified. |

## Active M1-A contracts

The executable research-state path is:

```text
Objective(objective_id, text)
Assumption(assumption_id, text)
Task(task_id, objective_id, kind, instruction, status)
PlanRevision(plan_revision_id, objective_id, task_bindings, dependencies, fingerprint)
ActivePlanRevisionSelection(objective_id, plan_revision_id)
DataProfile(data_profile_id, row_count, column_count, columns)
Evidence(evidence_id, task_id, data_profile_id, content, provenance, artifact_refs)
SessionFrame(objective, assumptions, tasks, evidences, data_profile)
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
DataProfile projection. Planner requests semantic bounded work through
`run_data_work`; it does not select the internal capability, provider, path, or
DataProfile identity. Application supplies authoritative execution context,
and the tool boundary performs execution-internal capability dispatch.
Data Explorer passes the requested semantic work, DataProfile/schema, and finite
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

The standalone Evidence-admission service does not append to `SessionFrame`.
The approved DATA runtime updates its current materialized frame with the
committed Objective and Task and later terminal Task status, but does not add
the computed result as Evidence. Canonical typed-reference membership,
active-profile selection, retained state, and restart reconstruction remain
**Deferred**.

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
Planner response synthesis is not Task work. The PlanRevision V1 domain and
side-effect-free candidate validation are **Implemented**, and its append-only
repository foundation is **Verified on SQLite**. Planner authoring, human
approval, exact post-approval validation and persistence, first activation,
active selection, and bounded DATA runtime use are **Implemented**. Durable
approval and recovery, active-plan replacement, complete lifecycle progression,
and scientific runtime remain **Deferred**.

## Verification qualification

Planner focused tests use deterministic fake model and dispatcher boundaries to
verify typed-state inspection, natural-language and explicit action parity,
explicit Objective and Assumption results with Application-side application,
exact transient canonical Objective, Task, and PlanRevision construction
without pre-approval mutation or dispatch, all three data capabilities,
approval/rejection without pending state, rejection, pending-plan replacement refusal,
atomic commit rollback, successful and blocked lifecycle transitions,
Evidence-free active-plan execution,
Evidence-grounded follow-up, Assumption quarantine, native model-history pass-
through, append-only complete-run turns, and in-process history retention. Full pytest collection
includes the rewritten Planner modules; the former three donor import blockers
are removed. Layer tests verify that Planner cannot import pandas, dataset
loaders, Data Explorer implementations, or deferred scientific and
PlanRevision contracts or SessionFrame directly. Architecture tests also prove
that Planner.run, graph State, and PlannerOutput have no SessionFrame surface.
Workspace ownership and documentation regressions retain their existing
boundaries. The vertical integration test additionally proves real CSV row-count
execution from an approved transient canonical plan through active PlanRevision, Data Explorer,
completed Task, and Planner response while creating zero Evidence. Dependency
tests prove `T1 -> T2`, prerequisite precedence over order and priority, no
completed-Task rerun, and typed missing-capability blocking. M3-A focused tests
additionally
execute real CSV and Parquet data, all seven allowlisted operations, explicit
Workspace and external paths under an arbitrary CWD, source-file immutability,
atomic candidate/profile/binding admission, Data Explorer-owned fake-planner
operationalization, successful and replayed Evidence admission, same-path
mutation, wrong-profile/path, unsupported/invalid planning, and zero-Evidence
failure paths.

Focused verification on 2026-08-11 ran:

```text
uv run pytest -q \
  tests/runtime/test_conversation.py \
  tests/agents/planner/test_model_adapter.py \
  tests/runtime/test_bootstrap_config.py \
  tests/agents/test_llm.py
```

Result after the bounded multi-provider configuration repair: **23 passed**.
Native conversation-history tests remain green. The four post-PR-#41 failures
were repaired by supplying canonical providers in Planner/bootstrap tests and
testing the generic `AgentFactory`; no active source or test references the
removed `OpenAICompatibleAgentFactory` name.

## Design target: dependency inversion

**Partially implemented.** Agents consume inward-facing dispatcher and model
factory contracts; runtime bootstrap constructs concrete execution, LLM, MCP,
skills, and workspace dependencies; dataset and persistence adapters live
under infrastructure; and CLI presentation is outside runtime core. Some
application services still use concrete SQLite persistence, and the `schemas`
package still mixes active bounded, workflow, provenance, and deferred donor
contracts. A domain-contract split remains a **Design target** and must not
create parallel FCO class families.
