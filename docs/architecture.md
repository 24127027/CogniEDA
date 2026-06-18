# Architecture Notes

## System Intent

CogniEDA is a memory-driven exploratory data analysis system. It is designed to preserve analytical continuity through explicit artifacts rather than through long conversational context. It should be implemented as an analytical system with structured state, not as a generic conversational assistant.

## Architectural Layers

### Artifact and Domain Contracts

Defines the core analytical artifacts such as projects, datasets, profiles, assumptions, hypotheses, evidence, decisions, and session frames. These contracts are the durable state model for the system.

### Analysis Workflow and Services

Encapsulates profiling, assumption generation, hypothesis definition, validation, evidence capture, and session framing. This layer should express analytical behavior in reusable services rather than in ad hoc entrypoint logic.

### Persistence and Repository Layer

Responsible for storing and retrieving artifacts, datasets, lineage, and historical states. This layer must preserve append-first history and explicit relationships.

### Interface and Orchestration Layer

Provides CLI or other future interfaces that coordinate workflows without owning business rules. Orchestration should remain thin relative to domain logic and artifact contracts.

## Core Operating Loop

The default analytical loop is:

`ingest/profile -> identify risks -> generate assumptions -> define hypotheses -> validate -> capture evidence -> log decisions -> emit session frame`

This loop is the preferred operational path for future implementations. Shortcuts that skip evidence capture or decision logging should be treated as architectural violations.

## State Model

- Distinguish active artifacts from archived artifacts explicitly.
- Prefer append-first history over in-place mutation.
- Use explicit supersession when artifacts are replaced or corrected.
- Preserve dataset lineage and evidence provenance as part of system state.
- Treat session continuity as a snapshot of active references, not as raw conversation replay.

## Deferred Implementation Boundaries

- No concrete schema definitions are locked in this document.
- No database technology choice is locked yet.
- No API contract is locked yet.
- No execution engine details are locked yet.
- No serialization, migration, or indexing strategy is locked yet.
