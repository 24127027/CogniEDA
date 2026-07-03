# Architecture Notes

This file is retained as a legacy entry point. The current documentation system lives under [docs/index.md](index.md).

Use these pages for implementation-oriented architecture:

- [Architecture Overview](architecture/overview.md)
- [First-Class Objects](architecture/first-class-objects.md)
- [Storage Layers](architecture/storage-layers.md)
- [Planner Workflow](architecture/planner-workflow.md)
- [Implementation Gap Analysis](architecture/implementation-gap-analysis.md)

## Current Status

The current implementation is a scaffold with target FCO schemas, SQLModel persistence, repositories, profiling utilities, `SessionFrame` snapshots, and planner/executor graph stubs.

The architecture defines exactly these FCOs: `Objective`, `DataProfile`, `Assumption`, `Task`, `Hypothesis`, `Evidence`, `Discovery`, and `SessionFrame`.

The largest remaining gaps are runtime behavior: operation-before-commit planner persistence, full execution/provenance records, executable DVC integration, graph retrieval policy, and evidence-cache services.
