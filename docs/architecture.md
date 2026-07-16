# Architecture Notes

This file is retained as a legacy entry point. The current documentation system lives under [docs/index.md](index.md).

Use these pages for implementation-oriented architecture:

- [Architecture Overview](architecture/overview.md)
- [First-Class Objects](architecture/first-class-objects.md)
- [Storage Layers](architecture/storage-layers.md)
- [Planner Workflow](architecture/planner-workflow.md)
- [Implementation Gap Analysis](architecture/implementation-gap-analysis.md)

## Current Status

The current implementation is a backend prototype with target FCO persistence, provenance/workflow records, profiling utilities, `SessionFrame` projections, approval-gated execution admission, and a durable local worker/finalization protocol. Answer/planning branches and concrete executor graphs remain scaffold-level.

The architecture defines exactly these FCOs: `Objective`, `DataProfile`, `Assumption`, `Task`, `Hypothesis`, `Evidence`, `Discovery`, and `SessionFrame`.

The largest remaining gaps are a working default natural-language path, general planner approvals, runnable executors, full reproducibility provenance, executable DVC/cleaning, graph retrieval, cache, static-quality compliance, and production service/worker bootstrap.