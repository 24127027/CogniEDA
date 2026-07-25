# CogniEDA Canonical Documentation Index

This is the navigation authority for current architecture, target constraints,
workflows, decisions, and structural-exit documentation. Source code remains the
authority for current implementation.

> [!IMPORTANT]
> **Core Thesis**: CogniEDA is a *validity-preserving research-state infrastructure* for governed analytical investigation.
> It is **not** a generic chat assistant, notebook wrapper, vector retrieval database, or long-memory chatbot.

---

## 1. Primary Entry Points

* [Project Purpose](project-purpose.md): Research intent vs. analytical infrastructure, core thesis, and design principles.
* [Roadmap](roadmap.md): Reviewed structural foundation, S4 checkpoint, and future Package 7 scope.
* [Structural Exit Status](architecture/structural-exit-status.md): Adversarial Package S4 assessment and qualified Package 7 verdict.

---

## 2. Architecture & Design

* [Architecture Overview](architecture/overview.md): System organization, core layers, and architectural invariants.
* [Research-State Model](architecture/research-state-model.md): Canonical First-Class Objects (FCOs), non-FCO boundaries, lifecycles, and immutability rules.
* [Scientific Specialist Authority](architecture/scientific-specialist-contracts.md): Data Explorer observation vs. Hypothesis Analyst proposal authority, responsibility matrix, and protected context boundaries.
* [Context Type Safety](architecture/context-type-safety.md): Context isolation rules (Planning, Execution, Conclusion, Governance, Retrieval) and Assumption quarantine.
* [Bounded Contexts](architecture/bounded-contexts.md): Package decomposition map (`research`, `execution`, `evidence`, `evaluation`, `governance`, `discovery`, `validity`, `runtime`, `retrieval`, `workflow`).
* [Runtime Composition](architecture/runtime-composition.md): In-process `CogniEDARuntime` composition and execution mechanics.
* [Persistence and Transactions](architecture/persistence-and-transactions.md): SQLModel storage facade, repository adapters, and sole transaction owners.
* [Validity and Invalidation](architecture/validity-and-invalidation.md): Immutable validity events, source fingerprints, and atomic invalidation propagation.
* [Retrieval and SessionFrame](architecture/retrieval-and-session-frame.md): Active `SessionFrame` context management, bounded retrieval, and active invalidation filtering.
* [Migrations and Schema Evolution](architecture/migrations.md): SQLite DDL migration entry point, trigger guards, and legacy quarantine.
* [Module Responsibilities](architecture/module-responsibilities.md): Complete module-level responsibility matrix across all bounded contexts.
* [Implementation Gap Analysis](architecture/implementation-gap-analysis.md): Implementation audit and historical progress record.

---

## 3. Workflows

* [Workspace and Data Profile Workflow](workflows/workspace-and-data-profile.md): Implemented profiling/persistence and the absent governed product workflow.
* [Task to Hypothesis Workflow](workflows/task-to-hypothesis.md): Planning, task formulation, and one-to-one hypothesis binding.
* [Execution to Evidence Workflow](workflows/execution-to-evidence.md): Analytical task dispatch, Data Explorer execution, and evidence admission.
* [Evidence to Discovery Workflow](workflows/evidence-to-discovery.md): Protected hypothesis evaluation, proposal synthesis, and atomic discovery materialization.
* [Governance and Admission Workflow](workflows/governance-and-admission.md): User decision recording, proposal authorization, and fenced claim validation.
* [Validity Propagation Workflow](workflows/validity-propagation.md): Authorized atomic dependent-state propagation and query-policy exclusion.
* [Session Resume and Retrieval Workflow](workflows/session-resume-and-retrieval.md): Append-only frame projections, retrieval, and the absent product bootstrap.

---

## 4. Architectural Decision Records (ADRs)

* [ADR-001: First-Class Research State](decisions/ADR-001-first-class-research-state.md): Selection of explicit typed research-state objects over generic chat/vector memory.
* [ADR-002: Assumption Quarantine](decisions/ADR-002-assumption-quarantine.md): Mandatory exclusion of Assumptions from Conclusion/Discovery synthesis contexts.
* [ADR-003: Specialist Scientific Authority](decisions/ADR-003-specialist-scientific-authority.md): Separation of Data Explorer observation from Hypothesis Analyst scientific proposals.
* [ADR-004: Atomic Discovery Admission](decisions/ADR-004-atomic-discovery-admission.md): `AtomicDiscoveryAdmissionService` as sole Discovery materialization transaction owner.
* [ADR-005: Atomic Validity Propagation](decisions/ADR-005-atomic-validity-propagation.md): `AtomicValidityPropagationService` as sole validity propagation transaction owner.
* [ADR-006: SQLite Supported Boundary](decisions/ADR-006-sqlite-supported-boundary.md): SQLite with immediate transaction locking as the sole supported persistence runtime.
* [ADR-007: No Supported CLI Before Product Bootstrap](decisions/ADR-007-no-supported-cli-before-product-bootstrap.md): Explicit deferral of CLI, HTTP server, and worker daemon entry points before Package 7 product bootstrap.

---

## 5. Development Guides

* [Development Setup](development/setup.md): Environment initialization and setup.
* [Testing Guide](development/testing.md): Automated test execution and guidelines.
* [Contributing Guidelines](development/contributing.md): Contribution guidelines and conventions.
* [Code Guidelines](development/guideline.md): Coding rules and style expectations.
* [Pull Request Template](development/pull_request_template.md): PR submission template.

---

## 6. Status language

Canonical pages label current implementation, target design, limitations, and
unsupported/deferred surfaces in prose. “Implemented” applies only to the
specific named boundary; it does not imply a CLI, service, worker, or production
adapter.
