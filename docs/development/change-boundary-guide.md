# Change-boundary guide

Use this page after reading the canonical concept owner. It identifies the
current source layers and the owner that must remain in control; it does not
grant authority to a package merely because the package stores a record.

## Research-state and lifecycle change

| Change | Start here and likely layers | Owner, tests, and required updates | Forbidden shortcut; decision record or migration trigger |
| --- | --- | --- | --- |
| Change an FCO field or lifecycle | [Research-state objects and roles](../concepts/research-state/objects-and-roles.md), relevant `src/schemas/research/` or `src/schemas/evidence/`; then validator, repository mapping, `src/db/models/`, and application reader/writer | The domain-specific application owner remains authoritative. Run matching `tests/schemas/`, repository tests, transition tests, and `tests/architecture/`; update canonical concept and contributor docs | Do not add an FCO field only to a table or bypass lifecycle checks. Create a decision record for changed invariant/meaning; create a migration for persisted shape or constraints. |
| Add non-FCO provenance | Classify it first; start at the nearest `src/schemas/execution/`, `evaluation/`, `governance/`, or `validity/` contract | The relevant transition owner writes it; test schema, repository, owner, and architecture classification; update contributor/current-state docs if behavior changes | Do not promote provenance to an FCO or create an alternate scientific writer. Use a decision record only for durable authority/provenance policy; create a migration if stored. |
| Change Task or Hypothesis admission | [Investigation lifecycle](../concepts/research-state/investigation-lifecycle.md), task/hypothesis schemas, Planner operation contract, and `commit_planner_operations` | `commit_planner_operations` owns ordinary approved admission; add Planner, repository, and architecture tests | Do not let proposed Tasks execute or bypass terminal/cardinality guards. Create a decision record for lifecycle policy; create a migration for durable contract/model changes. |
| Add a PlannerOperation | [Planner boundary](../operations/planner-and-approvals.md), `src/schemas/planner_operations.py`, planner nodes, and planner-operation repository | `commit_planner_operations` owns approved ordinary persistence. Run Planner, operation-repository, orchestrator, and architecture tests; update contributor and package docs | Do not make an operation an FCO or let it author scientific state. Create a decision record if it changes an approved workflow/authority policy; create a migration if the persisted schema changes. |
| Change ordinary Planner commit | `src/application/orchestrator/planner_commit.py`, its tests, and delegated execution staging | `commit_planner_operations` remains the transaction coordinator only for ordinary operations. Run planner, orchestrator, repository, and architecture tests | Do not call a scientific writer from arbitrary node code or give Planner an Evidence/Discovery writer. Create a decision record for durable ownership change; create a migration only if durable records change. |

## Execution, Evidence, and protected evaluation

| Change | Start here and likely layers | Owner, tests, and required updates | Forbidden shortcut; decision record or migration trigger |
| --- | --- | --- | --- |
| Add or modify execution lifecycle behavior | [Execution-to-Discovery](../concepts/scientific-lifecycle/execution-to-discovery.md), execution schemas/repositories, `src/application/execution/` | `ExecutionAttemptTransitionService` owns run, approval, lease, fencing, outbox/inbox transition behavior. Run transition, race, recovery, repository, and architecture tests | Do not commit inside a partial execution workflow or let a worker self-admit science. Create a decision record for lease/fencing/authority change; create a migration for stored lifecycle state. |
| Add a concrete Data Explorer | `src/schemas/execution/data_explorer.py`, registry/dispatcher, runtime composition, and execution receiver | It supplies typed observations only; `execute_evidence_admission_plan` and execution finalization remain the admission path. Run registry/dispatcher, execution, runtime, and architecture tests | Do not return interpretation, Discovery, or direct database writes. Create a decision record for capability or external-effect policy; create a migration only if durable execution contracts change. |
| Change Evidence admission | [Scientific authority](../concepts/scientific-lifecycle/scientific-authority.md), evidence plan/service, execution finalizer, evidence schema/repository | `execute_evidence_admission_plan` owns plan application. Run evidence-admission, scientific-commit race, repository, and architecture tests | Do not allow Data Explorer or repository code to interpret/admit partial Evidence. Create a decision record for evidence authority; create a migration for stored representation. |
| Change protected evaluation input | [Protected evaluation](../concepts/scientific-lifecycle/protected-evaluation.md), bundle schema/builder, evaluation transition service, Analyst contract | `EvaluationTransitionService` plus the bundle builder own evaluation lifecycle; the Analyst alone authors the typed proposal/failure. Run bundle, Analyst, evaluation transition/control, and architecture tests | Do not add Assumption, SessionFrame, Discovery, raw chat, or generic optional authority channels. A decision record is required for a new scientific input; create a migration if the durable bundle/control contract changes. |
| Change Discovery proposal fields | [Scientific authority](../concepts/scientific-lifecycle/scientific-authority.md), `src/schemas/evaluation/results.py`, bundle and proposal digest paths, governance/admission plans | Analyst proposal contract and exact-copy admission remain binding. Run schema, bundle-digest, Analyst, governance, admission, and E2E tests | Do not normalize/rewrite proposal fields in application or governance code. Create a decision record for scientific meaning/authority; create a migration if proposals/control records persist it. |

## Governance, admission, and validity

| Change | Start here and likely layers | Owner, tests, and required updates | Forbidden shortcut; decision record or migration trigger |
| --- | --- | --- | --- |
| Change governance authority or decisions | [Discovery governance and admission](../concepts/scientific-lifecycle/discovery-governance-and-admission.md), governance schemas/repositories, authority issuer, decision service | `GovernanceAuthorityIssuer` and `DiscoveryAdmissionGovernanceService` own distinct grants and exact decisions. Run governance authorization, decision-race, runtime, and architecture tests | Do not let governance author/edit scientific content or accept caller-created authority. Create a decision record for auth/decision policy; create a migration for durable grant/decision change. |
| Change atomic Discovery admission | admission plan, coordinator, `AtomicDiscoveryAdmissionService`, all participating repositories | `AtomicDiscoveryAdmissionService` owns the complete scientific cutover. Run admission-plan, atomic/race/rollback, repository guard, E2E, and architecture tests | Do not add a public repository writer, split commits, or have Planner/governance materialize Discovery. A decision record is required; create a migration for any changed persisted participant. |
| Change validity propagation | [Atomic validity propagation](../concepts/validity/validity-propagation.md), propagation command/plan/service, validity repository and retrieval | `AtomicValidityPropagationService` owns deterministic dependent cutover and ValidityEvent. Run propagation, replay/race, repository, retrieval, and architecture tests | Do not edit Evidence/DataProfile in place, select dependents at the caller, or author a replacement Discovery. A decision record is required for authority/effect policy; create a migration if records or constraints change. |

## Context, persistence, product, and configuration

| Change | Start here and likely layers | Owner, tests, and required updates | Forbidden shortcut; decision record or migration trigger |
| --- | --- | --- | --- |
| Change retrieval policy or ranking | [Context type safety and retrieval](../concepts/context/context-type-safety.md), retrieval request/schema, policy, engine, repositories | `DiscoveryRetrievalEngine` has read-only selection responsibility after authority filters. Run retrieval policy/engine, validity, and architecture tests | Do not score before validity/lifecycle filtering, imply semantic retrieval is implemented, or let a pin restore invalid state. Create a decision record for retrieval authority/scaling policy; create a migration only if durable retrieval state changes. |
| Change SessionFrame behavior | [SessionFrame and active context](../concepts/context/session-frame.md), frame schema/repository/builder, validity interaction | Frame builder owns projection; atomic admission owns a conclusion frame when part of scientific cutover. Run frame-builder, retrieval, validity, and architecture tests | Do not use a frame as protected evaluation input or rely on global/latest behavior as a future pattern. Create a decision record for durable scope/authority model; create a migration if stored frame semantics change. |
| Change persistence model | [Persistence ownership](../operations/persistence-and-transactions.md), schema, repository mapping, `src/db/models/`, affected owner | The application service still owns the transaction. Run schema/repository/model, DB equivalence, application, and architecture tests; update contributor/package docs | Do not make `db.models` the domain owner or introduce direct ORM writes in a new layer. Create a decision record for boundary/backend policy; a migration is normally required. |
| Add a migration | [SQLite initialization and migrations](../operations/sqlite-and-migrations.md), `src/db/migrations.py`, initializer, models, and legacy handling | A new upgrade step preserves historical compatibility. Run DB initialization, migration, equivalence, repository, and architecture tests | Never edit, reorder, or repurpose a historical migration. A migration is required for existing-database shape, data, index, or guard changes; create a decision record for immutable-history/backend policy. |
| Add a product entry point | [Product surface boundary](../operations/product-bootstrap.md), runtime/factory seam, authentication, adapters, and roadmap prerequisite | `CogniEDARuntime` composes injected dependencies; a product host is not yet an owner. Run runtime, adapter, recovery, E2E, and architecture tests | Do not advertise a CLI/API/worker/daemon before the coherent product boundary exists. A decision record is required for bootstrap/operational policy; create a migration as durable deployment state demands. |
| Change configuration, tools, or skills | `config/`, `skills/`, `src/tools/`, `src/agents/llm.py`, and runtime composition | ToolManager/configuration constructs capabilities; it has no scientific authority. Run tool manager, runtime, config/doc integrity, and any adapter tests | Do not claim checked-in MCP/skill configuration is runnable or treat a directory as a capability. Create a decision record for tool/security/deployment policy; create a migration only for durable configuration state. |

## Schema, repository, model, and migration checklist

For a domain field, first decide whether it is public domain meaning, an
application-validation input, a persistence mapping, or a physical storage
attribute. A change can touch schema, validation, repository mapping, model,
migration, tests, and documentation; it does not automatically touch every
layer.

A lifecycle state needs a larger review: enum and schema validators;
repository filters and active retrieval; application transitions; validity
effects; database constraints and compatibility; tests; and status/architecture
documentation. A persistence-only field must remain persistence-only unless a
separate deliberate design change promotes it. Historical migrations are not
editable. Add a new upgrade step and keep the known lack of immutable revision
identities explicit.

## Unsafe shortcuts

The following are rejected even when they appear convenient:

- Creating Discovery directly from Planner; see [Planner boundary](../operations/planner-and-approvals.md).
- Letting Data Explorer produce interpretation; see [scientific authority](../concepts/scientific-lifecycle/scientific-authority.md).
- Adding Assumptions to protected synthesis; see [protected evaluation](../concepts/scientific-lifecycle/protected-evaluation.md).
- Rewriting `DiscoveryProposal` in application code; see [governance and admission](../concepts/scientific-lifecycle/discovery-governance-and-admission.md).
- Letting governance edit scientific content; see [scientific authority](../concepts/scientific-lifecycle/scientific-authority.md).
- Adding a public repository writer for atomic scientific state; see [persistence ownership](../operations/persistence-and-transactions.md).
- Calling `session.commit()` inside one partial scientific workflow; see [atomic Discovery admission](../concepts/scientific-lifecycle/discovery-governance-and-admission.md).
- Using `GeneratedView` as Discovery; see [research-state objects and roles](../concepts/research-state/objects-and-roles.md).
- Mutating DataProfile or Evidence in place; see [validity over time](../concepts/validity/validity-over-time.md).
- Editing a historical migration; see [SQLite initialization and migrations](../operations/sqlite-and-migrations.md).
- Assuming SQLite behavior ports automatically; see [SQLite boundary](../operations/sqlite-and-portability.md).
- Treating an interface, directory, or TODO node as implemented capability; see [current state](../current-state.md).
- Adding semantic ranking before authority filters; see [retrieval strategy](../concepts/context/retrieval-strategy.md).
- Allowing pins to override invalid lifecycle state; see [active retrieval after invalidation](../concepts/validity/active-retrieval-after-invalidation.md).

## Package 7 entry paths

Do not begin Package 7 from a package name alone. Follow the roadmap gates.

- **7A:** begin at runtime/factory seams, the governance principal resolver,
  the Hypothesis Analyst model boundary, ToolManager/configuration, and the
  unresolved MCP/skill blocker.
- **7B:** begin at the observation-only Data Explorer contract, registry and
  dispatcher, execution result receiver, Evidence admission, and artifact policy.
- **7C:** begin at execution reconciliation, durable approval recovery,
  SessionFrame scoping, Planner composition debt, and restart coordination.
- **7D:** begins only after the 7A–7C exit criteria. Preserve observation-only
  execution, protected Analyst input, exact authority, and atomic admission.
