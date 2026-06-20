# Architecture Notes

## System Intent

CogniEDA is a memory-driven exploratory data analysis system for deep data investigation and long-running agent context management. It preserves analytical continuity through explicit artifacts instead of depending on long conversational buffers. It should be implemented as a structured analytical system, not as a generic conversational assistant.

## Architectural Layers

### Artifact and Domain Contracts

Defines the durable analytical artifacts such as projects, datasets, profiles, assumptions, hypotheses, evidence, decisions, and session frames. In the current scaffold, `SessionFrame` is the concrete persisted implementation of CogniEDA's broader `Context Frame` concept, including checkpoint, branch, handoff, stale-context, and tool-cache metadata.

### Analysis Workflow and Services

Encapsulates profiling, assumption generation, hypothesis definition, validation, evidence capture, decision logging, and session framing. This layer should express analytical behavior in reusable services rather than in ad hoc entrypoint logic.

### Persistence and Repository Layer

Responsible for storing and retrieving artifacts, datasets, lineage, historical states, and context-frame snapshots. This layer must preserve append-first history and explicit relationships.

- The local SQLModel store is the current runtime persistence surface for all first-class artifacts.
- Git-tracked JSON under `artifacts/` currently serves as reviewable metadata mirrors for `DatasetAsset` and `DataProfile`, not as a competing second runtime state model.
- Relationship-heavy links should use normalized association tables when they need referential integrity or typed semantics.
- JSON blobs are appropriate for snapshot payloads such as session-frame summaries, stale-context markers, dead-end notes, and cached tool-result metadata.

### Interface and Orchestration Layer

Provides CLI or future interfaces that coordinate workflows without owning business rules. Orchestration should remain thin relative to domain logic and artifact contracts.

## Core Operating Loop

The default analytical loop is:

`ingest/profile -> identify risks -> generate assumptions -> define hypotheses -> validate -> capture evidence -> log decisions -> emit session frame`

This remains the preferred operational path. Shortcuts that skip evidence capture, decision logging, or explicit context-frame updates should be treated as architectural violations.

## State Model

- Distinguish active artifacts from archived artifacts explicitly.
- Prefer append-first history over in-place mutation.
- Use explicit supersession when artifacts are replaced or corrected.
- Preserve dataset lineage and evidence provenance as part of system state.
- Treat session continuity as a typed context-frame snapshot, not as raw conversation replay.
- Allow memory items inside a frame to carry status, provenance, freshness, and invalidation rules.
- Record stale context, overruled context, and dead ends explicitly so they remain historical without polluting active reasoning.
- Treat tool-result caches as scoped analytical state with explicit invalidation.

## Deferred Implementation Boundaries

- The current local database scaffold is SQLite-first and repository-backed, but migration tooling is still pending.
- `SessionFrame` is the current concrete context-frame artifact; a separate `ContextFrame` artifact type is not introduced yet.
- No persistent memory-graph artifact is implemented yet.
- No automated invalidation engine is implemented yet; invalidation is contract-first metadata at this stage.
- No API contract is locked yet.
- No execution engine details are locked yet.
