# CogniEDA Documentation Index

This index defines document authority after the 2026-07-21 repository-wide alignment audit. Code
is the source of truth for current implementation. Project-owner decisions and documents marked
canonical below define target architecture. A current implementation note cannot override a
canonical target contract.

## Canonical Target Architecture

- [First-Class Objects](architecture/first-class-objects.md) — canonical FCO/non-FCO ontology,
  subordinate to `AGENTS.md` and explicit project-owner decisions.
- [Agent Responsibility Boundaries](architecture/agent-responsibility-boundaries.md) — canonical
  Planner, Hypothesis Analyst, Data Explorer, and Graph Miner contracts.
- [Scientific Specialist Contracts](architecture/scientific-specialist-contracts.md) — canonical
  subordinate contract specification separating Data Explorer observation from Hypothesis Analyst
  scientific evaluation under Agent Responsibility Boundaries.
- [Canonical Investigation Workflow](architecture/canonical-investigation-workflow.md) — canonical
  investigation, context, approval, persistence, error, and retry sequence.
- `AGENTS.md` — governing repository invariants and source precedence.

The canonical target files named by `AGENTS.md`, `first-class-object.txt` and
`user-agent-workflow.txt`, are not present in this workspace. The documents above make
the applicable project-owner decisions explicit; their absence must not be filled by guessing.

## Current Implementation And Status

- [Implementation Gap Analysis](architecture/implementation-gap-analysis.md) — concise maintained
  gap summary comparing current implementation against target design.
- [Architecture Overview](architecture/overview.md) — current/target system overview.
- Note: Verification audit reports are local-only artifacts under `.local/audits/` and remain uncommitted.

## Document Classification

| Document | Classification | Use |
| --- | --- | --- |
| `README.md` | Current but incomplete | Setup, verified repository commands, and brief status only |
| `docs/architecture/first-class-objects.md` | Canonical | FCO/non-FCO ontology |
| `docs/architecture/agent-responsibility-boundaries.md` | Canonical | Agent ownership and contracts |
| `docs/architecture/scientific-specialist-contracts.md` | Canonical | Subordinate contract specification for Data Explorer & Hypothesis Analyst |
| `docs/architecture/canonical-investigation-workflow.md` | Canonical | Target responsibility flow and current overlay |
| `.local/audits/*.md` | Local audit snapshot | Local-only verification artifacts under `.local/audits/` |
| `docs/architecture/overview.md` | Current but incomplete | Orientation, not detailed authority |
| `docs/architecture/planner-workflow.md` | Partially superseded | Current LangGraph topology note; canonical workflow prevails |
| `docs/architecture/executor-dispatch.md` | Implementation note rather than specification | Current durable generic adapter only; not target agent ownership |
| `docs/architecture/memory-model.md` | Current but incomplete | Memory/context model detail |
| `docs/architecture/storage-layers.md` | Current but incomplete | Storage inventory and target layering |
| `docs/architecture/session-frame.md` | Current but incomplete | SessionFrame snapshot implementation and target gap |
| `docs/architecture/provenance-and-cache.md` | Current but incomplete | Provenance/cache implementation note |
| `docs/workflows/user-research-workflow.md` | Partially superseded | User-facing elaboration; canonical investigation workflow prevails |
| `docs/workflows/task-to-discovery-lifecycle.md` | Partially superseded | Local lifecycle guard note; responsibility document prevails |
| `docs/workflows/data-profiling-and-cleaning.md` | Current but incomplete | Profiler and missing cleaning workflow |
| `docs/concepts/*.md` | Current but incomplete | Concept explanations subordinate to canonical architecture |
| `docs/architecture.md`, `docs/persistence.md`, `docs/data_versioning.md`, `docs/artifacts.md` | Historical context only | Compatibility entry points; do not use as complete runtime truth |
| `docs/idea.md` | Historical context only | Ideation, not normative ontology or implementation status |
| `src/**/README.md`, `config/README.md`, `skills/README.md` | Implementation note rather than specification | Package-local behavior/examples only |
| `docs/development/*.md` | Current guidance or historical snapshot | Developer workflow; verification snapshots may become stale |
| `docs/reference/glossary.md` | Current but incomplete | Terminology; canonical contracts prevail on conflict |

No file is deleted by this audit. Partially superseded documents remain useful implementation
notes, but they are no longer co-equal target specifications.

## Architecture Topics

- [Memory Model](architecture/memory-model.md)
- [Storage Layers](architecture/storage-layers.md)
- [Planner Workflow](architecture/planner-workflow.md)
- [Executor Dispatch](architecture/executor-dispatch.md)
- [SessionFrame](architecture/session-frame.md)
- [Provenance And Cache](architecture/provenance-and-cache.md)

## Workflows And Concepts

- [User Research Workflow](workflows/user-research-workflow.md)
- [Data Profiling And Cleaning](workflows/data-profiling-and-cleaning.md)
- [Task To Discovery Lifecycle](workflows/task-to-discovery-lifecycle.md)
- [Object Lifecycle](concepts/object-lifecycle.md)
- [Context Type Safety](concepts/context-type-safety.md)
- [Validity Basis](concepts/validity-envelope.md)

## Development And Reference

- [Setup](development/setup.md)
- [Testing](development/testing.md)
- [Contributing](development/contributing.md)
- [Glossary](reference/glossary.md)
