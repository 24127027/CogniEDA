# Architecture Notes

This file is retained as a legacy entry point. The current documentation system lives under [docs/index.md](index.md).

Use these pages for implementation-oriented architecture:

- [Architecture Overview](architecture/overview.md)
- [First-Class Objects](architecture/first-class-objects.md)
- [Storage Layers](architecture/storage-layers.md)
- [Planner Workflow](architecture/planner-workflow.md)
- [Implementation Gap Analysis](architecture/implementation-gap-analysis.md)

## Current Status

The current implementation is a scaffold with Pydantic schemas, SQLModel persistence, repositories, profiling utilities, `SessionFrame` snapshots, and planner graph stubs.

The final target architecture defines exactly these FCOs: `Objective`, `DataProfile`, `Assumption`, `Task`, `Hypothesis`, `Evidence`, `Discovery`, and `SessionFrame`.

The current code still uses older scaffold artifacts such as `Project`, `DatasetAsset`, and `DecisionLog`. See the gap analysis before making architecture changes.
