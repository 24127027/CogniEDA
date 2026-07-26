# Contributor documentation

This section maps CogniEDA's current implementation to source and tests. It
does not define the research-state concepts themselves. Start with the
[canonical reader journey](../index.md) for meaning, invariants, and product
status; use these pages to choose a safe change location.

## Before editing

1. Read the relevant canonical concept page and the [current state](../current-state.md).
2. Classify the proposed object or change: FCO, workflow state, provenance,
   cache, filesystem artifact, or generated view.
3. Find the application or authority owner in the [code orientation](code-orientation.md).
4. Read the focused tests before changing their boundary. Do not infer a
   product capability from a protocol, directory, or isolated test fixture.
5. Use the [change-boundary guide](change-boundary-guide.md) to identify every
   affected layer, required documentation, and whether an ADR or migration is
   needed.

The tracked default configuration is not a runnable product deployment. There
is no supported CLI, HTTP API, worker, daemon, concrete Data Explorer, or
default production Analyst adapter. The supported surface is an in-process
library foundation with explicit dependency injection; see
[product bootstrap](../operations/product-bootstrap.md).

## What to read

| Need | Read first | Then inspect |
| --- | --- | --- |
| Meaning and invariant | [Canonical reader journey](../index.md) | relevant schema, owner, and focused test |
| Current maturity or known deviation | [Current state](../current-state.md), [capability map](../capability-and-maturity-map.md), and [roadmap](../roadmap.md) | source only after the status boundary is clear |
| Durable architectural rationale | [Design decisions and tradeoffs](../design-decisions/index.md) and the linked ADR | owner and architecture tests |
| Source responsibility and transaction owner | [Code orientation](code-orientation.md) | local package README and focused tests |
| Where a change belongs | [Change-boundary guide](change-boundary-guide.md) | schema, repository, model, migration, and application owner |
| Test selection and commands | [Testing strategy](testing.md) | nearest focused test and `tests/architecture/` |
| Local install or in-process composition | [Development setup](setup.md) | runtime composition and configuration references |

## Bounded reading tracks

### Research-state change

[Research-state objects and roles](../concepts/research-state/objects-and-roles.md) -> [change guide](change-boundary-guide.md#research-state-and-lifecycle-change) -> relevant `src/schemas/` contract -> repository and `src/db/models/` mapping -> application owner -> focused schema, repository, and architecture tests.

### Scientific lifecycle change

[Scientific authority](../concepts/scientific-lifecycle/scientific-authority.md) -> [protected evaluation](../concepts/scientific-lifecycle/protected-evaluation.md) -> [governance and admission](../concepts/scientific-lifecycle/discovery-governance-and-admission.md) -> transaction owner -> race, replay, rollback, and architecture tests.

### Planner change

[Planner boundary](../operations/planner-and-approvals.md) -> `PlannerOperation` schema -> `src/application/orchestrator/planner_commit.py` -> delegated transaction owner -> `tests/agents/planner/`, `tests/application/orchestrator/`, and architecture tests.

### Retrieval or SessionFrame change

[Context type safety and retrieval](../concepts/context/context-type-safety.md) -> [SessionFrame scaling boundary](../concepts/context/session-frame-scaling.md) -> `src/memory/` -> `tests/memory/` and validity/architecture tests.

### Persistence or migration change

[Persistence and transactions](../operations/persistence-and-transactions.md) -> [SQLite boundary](../operations/sqlite-and-portability.md) -> [SQLite initialization and migrations](../operations/sqlite-and-migrations.md) -> schema, model, repository, migration code -> `tests/db/`, `tests/repositories/`, and architecture tests.

### Product integration change

[Current state](../current-state.md) -> [roadmap](../roadmap.md) -> [product bootstrap boundary](../operations/product-bootstrap.md) -> runtime and adapter seams. Package 7 work begins only at the prerequisite named in the roadmap; this guide does not make a product surface supported.

## Documentation audiences

- **Reader documentation** is the canonical conceptual journey in `docs/index.md`.
- **Contributor documentation** is this development section: source navigation,
  change boundaries, testing, and setup.
- **Package references** are local `README.md` files under `src/`, `config/`,
  and `skills/`; they explain mechanics, not canonical concept ownership.
- **Local audits** under `.local/` are ignored checkout evidence. They are not
  reader or contributor documentation and must not become product claims.

## Technical-reference navigation

Use a technical reference only after its canonical owner and this contributor
hub establish the concept and safe change boundary. The retained references are
grouped by the implementation question they answer:

- [Architecture references](../architecture/overview.md) cover module,
  persistence, migration, runtime, specialist, retrieval, and validity
  mechanics. Their source-oriented gaps remain in the
  [implementation-gap analysis](../architecture/implementation-gap-analysis.md).
- [Workflow references](../workflows/task-to-hypothesis.md),
  [execution to Evidence](../workflows/execution-to-evidence.md),
  [governance and admission](../workflows/governance-and-admission.md), and
  [validity propagation](../workflows/validity-propagation.md) preserve exact
  preconditions, transitions, replay, and failure sequencing.
- Local package contracts begin at [application](../../src/application/README.md),
  [Data Explorer adapters](../../src/agents/executor/README.md),
  [SQLModel models](../../src/db/models/README.md), and
  [tools/configuration](../../src/tools/README.md). They are implementation
  mechanics, not current-state or conceptual owners.

The [configuration reference](../../config/README.md) and
[skills reference](../../skills/README.md) document the known unresolved
MCP/skill configuration gap; neither makes the checked-in defaults runnable.

## Common change paths

Use the [change-boundary guide](change-boundary-guide.md) for the detailed path
for an FCO or lifecycle field, a non-FCO provenance record, Planner operations,
execution and Evidence, protected evaluation, governance, Discovery admission,
validity, retrieval, SessionFrame, persistence/migrations, product seams, and
tools/configuration. Every path names the owner that must remain in control.

## Testing and documentation responsibilities

Run the tests owned by the changed layer before broad checks. The
[testing strategy](testing.md) explains what each test family proves and when a
full run is warranted. Update:

- canonical pages for meaning, invariants, authority, or durable decisions;
- current-state pages for maturity, deviations, supported boundaries, or
  Package 7 readiness;
- contributor pages for source ownership, test locations, or change workflow;
- a package README only for local mechanics; and
- an ADR for a durable invariant, backend policy, architectural decision, or
  product-bootstrap policy.

## Technical-reference maintenance

Retained technical references are already classified and linked to their
canonical concept and contributor owners. Update them when their source-level
mechanics change, but do not let them regain conceptual or global maturity
ownership. Consolidation, relocation, retirement, or redirection still requires
an explicit unique-content and inbound-link review; it is not incidental
cleanup for an ordinary contributor change. Checkout-specific matrices and
verification results remain ignored local evidence.
