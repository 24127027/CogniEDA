# CogniEDA current state

> **Implementation status:** **Partially implemented** overall. The guarded
> research-state and scientific-admission paths are **Implemented**, with their
> load-bearing persistence behavior **Verified on SQLite**. A supported product
> process and its production adapters are **Unsupported**.

This page is the canonical owner of current project maturity. It answers what
CogniEDA is today, what works on the supported in-process path, what remains
partial, and what is explicitly unsupported. The
[capability and maturity map](capability-and-maturity-map.md) provides a compact
comparison by domain, while the [roadmap](roadmap.md) owns future dependencies
and exit criteria.

## Current system boundary

CogniEDA is validity-preserving research-state infrastructure for governed
analytical investigation. Today it is an in-process Python library and runtime
composition root backed by workspace-local SQLite. It is neither an end-user
application nor a generic chat-memory system.

The supported boundary starts when a caller supplies an explicit database URL,
an authenticated-principal resolver, a Hypothesis Analyst model, and one Data
Explorer identity and factory. `CogniEDARuntime` composes those dependencies
with the Planner, execution coordination, and the scientific application
services. The runtime fails closed when required adapters are absent.

That boundary is useful and functional: callers can exercise guarded library
workflows and all canonical transaction owners in one process. It does not
provide command parsing, an HTTP lifecycle, a worker supervisor, deployment
identity, provider configuration, or a complete user interaction.

## Implemented research-state infrastructure

The domain model has exactly eight First-Class Objects:

- `Objective`
- `DataProfile`
- `Assumption`
- `Task`
- `Hypothesis`
- `Evidence`
- `Discovery`
- `SessionFrame`

Workflow, provenance, governance, cache, and presentation records remain
separate. In particular, `PlannerOperation`, `AnalysisFrame`, `ExecutionRun`,
`ValidityEvent`, and future `GeneratedView` or cache entries are not promoted
into scientific knowledge.

The supported repository and schema paths provide:

- immutable scientific payloads for `DataProfile` and `Evidence`;
- append-oriented Objective revision provenance;
- Task hierarchy, lifecycle, motivation, and analytical-eligibility guards;
- at-most-one Task-to-Hypothesis and Hypothesis-to-Discovery cardinality;
- parent-Task exclusion from Hypothesis and Discovery creation;
- durable workflow, execution, evaluation, governance, and validity records;
  and
- layered schema, repository, application, architecture-test, and selected
  SQLite enforcement.

The last boundary is intentionally qualified. Supported application paths are
guarded, but direct ORM or SQL access with database credentials is not an
absolute security boundary.

## Implemented scientific lifecycle

The guarded scientific spine is **Implemented**:

```text
approved terminal analytical Task
  -> approved execution contract
  -> durable ExecutionRun and outbox attempt
  -> observation-only Data Explorer result
  -> atomic AnalysisFrame and Evidence admission
  -> protected Hypothesis evaluation
  -> exact persisted Discovery proposal
  -> principal-bound governance decision
  -> atomic Discovery and conclusion-state admission
```

Authority remains separated along that path:

| Boundary | Current owner | Current status | SQLite qualification |
| --- | --- | --- | --- |
| ordinary approved Planner mutation | `commit_planner_operations` | **Implemented** | focused operation persistence is **Verified on SQLite** |
| execution attempt transitions | execution application services | **Implemented** | **Verified on SQLite** |
| AnalysisFrame and Evidence materialization | atomic Evidence admission | **Implemented** | **Verified on SQLite** |
| scientific wording | protected Hypothesis Analyst evaluation | **Implemented** | not a backend-specific claim |
| proposal authorization | governance authority and decision services | **Implemented** | **Verified on SQLite** |
| Discovery materialization | `AtomicDiscoveryAdmissionService` | **Implemented** | **Verified on SQLite** |
| dependent validity effects | `AtomicValidityPropagationService` | **Implemented** | **Verified on SQLite** |

The Data Explorer can report typed observations but cannot evaluate or persist
them. The Hypothesis Analyst receives a closed, repository-built synthesis
bundle and has no tools or raw-data access. Governance can authorize, reject,
or cancel the exact proposal but cannot rewrite it. Discovery admission copies
the authorized proposal exactly and commits the scientific state change
atomically.

Technical execution failure, evaluation failure, governance rejection or
cancellation, stale authority, and changed-binding conflicts fail without
creating a Discovery. Replay, claim, lease, and fencing behavior exists where
the owning workflow requires it.

## Implemented active-context and validity controls

Validity propagation is **Implemented** and **Verified on SQLite** for the
supported DataProfile, AnalysisFrame, Evidence, and ExecutionRun source
commands. The service:

- binds source, request, and deterministic-plan fingerprints;
- writes an immutable `ValidityEvent`;
- applies the complete dependent lifecycle plan atomically;
- preserves history while removing invalid state from active use; and
- distinguishes exact replay from changed-request conflict.

SessionFrame persistence, append-oriented snapshots, planning and answer
projections, pins, exclusions, inclusion reasons, and validity supersession are
**Partially implemented** as a continuity boundary. Protected Discovery
synthesis does not trust SessionFrame contents; it rebuilds its scientific
inputs from authoritative repositories.

Retrieval is also **Partially implemented**. It loads structural candidates,
applies lifecycle and context-role exclusions, and then performs deterministic
lexical ranking within a bounded result budget. This keeps authority safe, but
it is not semantic retrieval and does not provide Graph Miner traversal.

## Partial Planner and continuity workflows

The Planner is **Partially implemented**. Supported library paths include:

- explicit request commands and controlled natural-language understanding when
  a coherent model configuration is injected;
- Task proposal, approval, repository-current revalidation, and commit;
- governed Task decomposition with successor SessionFrame creation;
- Objective creation and update with revision provenance;
- fresh execution preparation and durable execution approval;
- identity-based resume of durable Planner operations and execution approvals;
  and
- delegation of approved ordinary mutations to
  `commit_planner_operations`.

The following boundaries remain incomplete or absent:

- answerability, direct answering, research-direction suggestion, result
  review, conflict review, pause, dataset/profile/cleaning, and project closure;
- natural-language Assumption creation, testability review, replacement, and
  conflict workflows;
- arbitrary LangGraph-node recovery after process restart;
- complete user-, Objective-, session-, and branch-scoped SessionFrame
  selection; and
- a user-facing continuity and governance experience.

Durable records therefore support bounded restart recovery, but they do not
constitute complete product conversation or workflow resume.

## Current runtime and persistence boundary

`CogniEDARuntime` and the external `COGNIEDA_RUNTIME_FACTORY` loader seam are
**Implemented**. Runtime construction uses explicit dependency injection and
initializes the database before composing application services. The factory
loader imports and type-checks a deployment-supplied runtime factory; it does
not define a deployment by itself.

SQLite is the only verified persistence boundary. Initialization applies the
targeted upgrade sequence, creates current SQLModel tables, installs selected
guards, and performs fail-closed legacy quarantine. Scientific admission,
validity, replay, fencing, and concurrency claims in this documentation are
qualified as **Verified on SQLite** where focused evidence exists.

PostgreSQL, other relational backends, multi-process writers, distributed
transactions, online migrations, and a mechanically immutable migration
revision registry are **Unsupported** or **Deferred**. They must not be inferred
from the relational abstractions.

## Unsupported product surfaces

The following are **Unsupported**:

- a packaged CogniEDA CLI;
- an HTTP or gRPC API;
- a production worker or daemon;
- a Python product-bootstrap implementation;
- a production principal or identity provider;
- a configured production Hypothesis Analyst provider;
- a concrete production Data Explorer;
- a user approval, cancellation, review, and output-delivery interface;
- a restart supervisor and durable coordination loop;
- Graph Miner traversal and persistent semantic or vector indexing; and
- one supported persistent end-to-end product slice.

The checked-in agent configuration is a **Known deviation** and a configuration
blocker for model-backed configured adapters. It references MCP servers that
are not defined in the active MCP configuration and skill directories that
contain no tracked `SKILL.md` definitions. `ToolManager` rejects the undefined
MCP reference explicitly. Minimal injected library paths can avoid that
construction, but the defaults are not a runnable deployment.

## Known deviations

The most consequential accepted differences from the preferred design are:

- SessionFrame lookup is database-global rather than scoped to a user,
  session, Objective, or branch; ordinary predecessor frames can remain active,
  and pin-only freshness is incomplete;
- Objective frame succession also uses the database-global latest frame;
- retrieval request Objective and SessionFrame identities are not effective
  filters, operation-scope admission is absent, and ineligible-profile
  candidates can consume the bounded context budget;
- the scorer has a semantic protocol name but the default behavior is lexical;
- Planner nodes still compose some sessions and repositories directly;
- an existing nonterminal Hypothesis cannot yet complete the intended
  execution-reuse path, which fails closed at lifecycle enforcement;
- an execution approval can remain `APPROVED` after a later admission failure
  without a complete recovery transition;
- some Planner route labels describe branches whose behavior is still absent;
- targeted migration history lacks immutable revision identities;
- database-level payload immutability is selective rather than universal; and
- checked-in MCP and skill configuration is unresolved.

These deviations do not create an alternate scientific writer on the current
in-process path. They become blocking when a product slice introduces real
users, repeated restarts, multiple sessions, or operational recovery.

## Practical consequences of incomplete boundaries

| Incomplete boundary | Practical consequence |
| --- | --- |
| production identity | authority contracts exist, but no supported deployment resolves a real principal |
| concrete Data Explorer | execution coordination exists, but no supported adapter produces observations from a real dataset |
| process-local graph checkpointing | durable approvals can be reconstructed, but arbitrary graph-node progress is lost on restart |
| global SessionFrame selection | multiple users, Objectives, sessions, or branches cannot reliably identify the intended active frame |
| lexical-only retrieval | authority remains safe, but recall and context-budget efficiency degrade as the research state grows |
| missing product interaction | users cannot exercise the complete proposal, approval, review, invalidation, and resume model through a supported interface |

## What the project is ready for next

The guarded library foundation is suitable for a bounded product-integration
package, provided future work preserves the existing authority and transaction
owners. The required dependency order is:

1. trusted local identity, a production Analyst adapter, and coherent
   deployment capability configuration;
2. one concrete observation-only Data Explorer;
3. restart-safe in-process coordination and scoped continuity; and
4. one persistent end-to-end product slice that exposes explicit unsupported
   edges.

These are roadmap dependencies, not claims that Package 7 behavior already
exists. See the [roadmap](roadmap.md) for blocker classifications and observable
exit criteria.

## Implementation orientation

- runtime composition: `src/application/runtime.py` and
  `src/application/runtime_loader.py`
- Planner coordination: `src/agents/planner/` and
  `src/application/orchestrator/`
- execution and Evidence: `src/application/execution/`,
  `src/agents/executor/`, and `src/application/evidence/`
- evaluation, governance, and Discovery:
  `src/application/evaluation/`, `src/application/governance/`, and
  `src/application/discovery/`
- validity: `src/application/validity/`
- research state and persistence: `src/schemas/`, `src/repositories/`, and
  `src/db/`
- active context and retrieval: `src/memory/`
- configuration and agent capabilities: `config/`, `skills/`, and `src/tools/`

For technical detail, continue with the
[architecture overview](architecture/overview.md), the
[implementation gap analysis](architecture/implementation-gap-analysis.md),
and the [product surface boundary](product-surface-and-bootstrap-boundary.md).
