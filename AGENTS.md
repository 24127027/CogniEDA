# CogniEDA Agent Guide

## Project Purpose

CogniEDA is a hypothesis-driven exploratory data analysis system with structured analytical memory.

The system has two core goals:

1. Reduce context rot through durable, structured analytical artifacts.
2. Support iterative data investigation through assumptions, hypotheses, validation, evidence, decisions, and session continuity.

The memory model is agent-agnostic. It is not only for one coding agent or one EDA workflow. The current concrete persisted implementation of the broader `Context Frame` idea is `SessionFrame`.

## Non-Goals

- CogniEDA is not a generic chatbot.
- CogniEDA is not a free-form conversational memory store.
- CogniEDA is not an unstructured notebook replacement.
- CogniEDA is not a system that silently mutates raw data.
- CogniEDA is not a system that treats interpretation as fact.

## Core Artifact Types

The following artifact types are first-class repository concepts and future code must preserve them explicitly:

- `Project`
- `DatasetAsset`
- `DataProfile`
- `Assumption`
- `Hypothesis`
- `Evidence`
- `DecisionLog`
- `SessionFrame`

See [docs/artifacts.md](/D:/mduy/source/repos/CogniEDA/docs/artifacts.md) for the canonical artifact contract.

## Memory Discipline

- Prefer structured artifacts over chat summaries.
- Reconstruct working context from active artifacts, not from conversation history.
- Separate durable facts from transient reasoning.
- Mark superseded, archived, rejected, and active states explicitly.
- When context is carried forward, preserve memory status, provenance, and invalidation rules where the contract allows them.
- Preserve provenance for every material analytical conclusion.
- Do not compress away evidence lineage or dataset/version references.
- Treat session continuity as an artifact problem, not a prompt-length problem.
- Keep stale, overruled, and dead-end context historically visible without letting it silently influence active reasoning.
- Treat checkpoints, branch labels, and cached tool results as explicit context data when they matter.

## Hypothesis, Evidence, and Decision Discipline

- Hypotheses must be testable and tied to explicit variables, scope, and validation method.
- Evidence must record dataset/version, method, parameters, result summary, limitations, and references to related assumptions and hypotheses.
- Decisions must record what was chosen, why it was chosen, what evidence supported it, and what alternatives were rejected.
- No claim of validation is acceptable without linked evidence.
- Interpretations must remain distinct from observations and recorded results.
- Inconclusive results remain evidence; they do not justify silent promotion of a hypothesis to supported or refuted.

## Data Safety Rules

- Never overwrite raw data.
- Prefer versioned or reversible transformations.
- Record row drops, column drops, imputations, filters, joins, and derived datasets explicitly.
- Preserve lineage from derived datasets back to source datasets.
- Flag leakage risks, missingness risks, confounding risks, sample-size instability, and suspicious shortcuts.
- If a transformation cannot be explained and reproduced, it is not acceptable.

## Architectural Preferences

- Python-first implementation managed with `uv`.
- Source code should follow a `src/`-oriented layout.
- Pydantic models should define artifact contracts once implementation begins.
- Prefer modular services and repositories over monolithic orchestration.
- Prefer deterministic utilities where possible.
- Preserve explicit artifact relationships rather than relying on inferred state.
- Keep CLI or orchestration layers thin relative to reusable domain logic.

## Testing Expectations

- Unit tests should cover deterministic artifact logic, controlled vocabularies, and validation rules.
- Integration tests should cover artifact persistence and workflow boundaries once those layers exist.
- Tests should verify traceability, state transitions, and reproducibility, not only happy-path outputs.
- Evidence-producing logic should be testable without hidden global state.
- Future tests must distinguish facts, assumptions, hypotheses, evidence, and interpretations in assertions.

## Repo Structure Guidance

Target structure guidance for future implementation:

- `src/`: domain artifacts, services, repositories, orchestration, and CLI/app entrypoints.
- `docs/`: durable architecture and artifact references.
- `tests/`: unit and integration coverage.
- `data/` or equivalent future location: versioned local data assets and derived outputs, if introduced later.

Current storage split:

- The local SQLModel store is the runtime persistence surface for all first-class artifacts.
- `artifacts/dataset_assets/` and `artifacts/data_profiles/` are Git-tracked metadata mirrors for reviewable dataset lineage and profile snapshots.
- Other first-class artifacts are currently DB-backed in the scaffold unless an explicit export/import flow is added later.

This is guidance for the intended shape of the repository. Step 3 does not require all directories or modules to exist yet.

## Hard Rules for Agents

- Do not invent evidence.
- Do not present assumptions or interpretations as facts.
- Do not bypass artifact creation or update rules in implementation.
- Do not create hidden mutable state outside explicit artifacts.
- Do not continue from stale context when active artifacts disagree.
- Do not silently mutate raw inputs, lineage, or artifact status.
- Do not collapse distinct artifact types into generic notes or free text.
- Do not treat a user prompt alone as durable project state when an artifact should exist instead.
