# Source layout

The Python package is organized by implementation ownership. This layout does
not redefine the canonical research architecture; it makes the current source
boundary explicit so that new work enters the correct package.

| Package | Current responsibility |
| --- | --- |
| `agents` | Planner and peer specialist role adapters. Planner owns human-facing coordination tools; Data Explorer owns direct dataset operations. Hypothesis Analyst and Graph Miner remain deferred scaffolds. |
| `application` | Inward-facing ports plus application-authority services for execution admission, Planner-operation commit, and guarded transitions. These services do not establish the complete canonical workflow. |
| `cli` | Installed command parsing, the development REPL, and terminal rendering. |
| `execution` | Role-neutral capability, request/result transport, provider registry, and dispatcher contracts. |
| `infrastructure` | Concrete dataset, DVC, LLM, MCP, skills, agent-tooling, and SQLite persistence adapters. DVC and external MCP execution remain unsupported. |
| `retrieval` | Lifecycle-aware eligibility policy, deterministic scoring, and a deferred Discovery-retrieval donor boundary. It is not a generic memory subsystem. |
| `runtime` | Workspace loading, explicit dependency composition, runtime messages, and the in-process `Application` boundary. |
| `schemas` | Typed research-state, workflow, provenance, and retrieval contracts retained from the current implementation. Separating active domain contracts from deferred donor contracts remains bounded structural debt. |

The dependency expectations are:

```text
schemas and execution contracts
        -> application ports and services
        -> agents
        -> runtime composition
        -> cli

infrastructure implements or supplies outward adapters
runtime/bootstrap is allowed to know concrete implementations
```

The graph is intentionally practical rather than a textbook layering exercise.
The enforced boundaries are more important than package names:

- Planner must not import pandas, dataset loaders, or Data Explorer profiling
  implementations. It delegates through typed execution contracts.
- Direct dataset loading is infrastructure; direct dataset operations are Data
  Explorer-owned.
- The product repository contains code and development resources, while the
  resolved `Workspace.root` owns conventional user research data and private
  operational state. See [Workspace ownership](workspace-layout.md).
- Generic execution infrastructure is not an agent.
- Application and execution code must not depend on CLI presentation.
- Runtime bootstrap owns concrete construction. Agent creation must not create
  mutable global tooling or read repository-relative configuration implicitly.
- Persistence implementations live under infrastructure and are verified only
  on SQLite.
- Removed historical packages (`data`, `db`, `memory`, `repositories`,
  `runtime.orchestrator`, and `tools`) are not compatibility import surfaces.

## Verified boundary

**Implemented.** Focused architecture tests enforce the Planner dataset-access
boundary, inward-layer independence from CLI, peer specialist package paths,
removed-package hard cutovers, and the absence of non-Python artifacts in the
production package tree. Workspace ownership regressions also reject
product-root research-state directories, package-relative user-data lookup,
and production references to test fixture paths.

**Partially implemented.** Dependency injection is explicit for execution,
model construction, and agent tooling, but some application services still use
the current concrete SQLite persistence boundary. The `schemas` package also
retains mixed active and deferred contracts. A future split must classify those
contracts first and must not create parallel FCO definitions.
