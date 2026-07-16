# CogniEDA Documentation Index

This documentation separates implemented behavior from target architecture. Use code as the source of truth for current behavior, and use the internal design documents as the source of truth for intended behavior.

## Implementation Status

- [Source Implementation Status](implementation/SRC_IMPLEMENTATION_STATUS.md)
- [Documentation/Source Drift Audit](implementation/DOC_SRC_DRIFT_AUDIT.md)
- [Vietnamese Source Codebase Audit](implementation/SRC_CODEBASE_REPORT_VI.md)

These reports are pinned to the audited Git commit stated in each file. For newer commits, re-verify source and tests before treating their status as current.

## Architecture

- [Overview](architecture/overview.md)
- [First-Class Objects](architecture/first-class-objects.md)
- [Memory Model](architecture/memory-model.md)
- [Storage Layers](architecture/storage-layers.md)
- [Planner Workflow](architecture/planner-workflow.md)
- [SessionFrame](architecture/session-frame.md)
- [Provenance And Cache](architecture/provenance-and-cache.md)
- [Implementation Gap Analysis](architecture/implementation-gap-analysis.md)

## Workflows

- [User Research Workflow](workflows/user-research-workflow.md)
- [Data Profiling And Cleaning](workflows/data-profiling-and-cleaning.md)
- [Task To Discovery Lifecycle](workflows/task-to-discovery-lifecycle.md)

## Concepts

- [Object Lifecycle](concepts/object-lifecycle.md)
- [Context Type Safety](concepts/context-type-safety.md)
- [Validity Envelope](concepts/validity-envelope.md)

## Development

- [Setup](development/setup.md)
- [Testing](development/testing.md)
- [Contributing](development/contributing.md)

## Reference

- [Glossary](reference/glossary.md)

## Legacy Notes

The older flat docs under `docs/artifacts.md`, `docs/architecture.md`, `docs/persistence.md`, and `docs/data_versioning.md` are compatibility entry points, not complete runtime truth. `docs/idea.md` is historical ideation and is not normative ontology. Prefer the implementation reports and indexed architecture tree for current code/target comparison.
