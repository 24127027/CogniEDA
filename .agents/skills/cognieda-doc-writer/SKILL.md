---
name: cognieda-doc-writer
description: Maintain CogniEDA repository documentation while preserving current-vs-target truth. Use when updating README, AGENTS.md, docs architecture/workflow/concept/development/reference pages, implementation gap analysis, or documentation that compares audited code with CogniEDA target design.
---

# CogniEDA Doc Writer

Use this skill to maintain CogniEDA documentation without overclaiming implementation status.

## Required Workflow

1. Inspect relevant source code before editing docs.
2. Inspect existing docs that cover the same topic.
3. Classify each concept as one of:
   - `Implemented`
   - `Partially implemented`
   - `Design target`
   - `Not implemented`
   - `Implementation deviates from target`
   - `Unclear from code`
4. Separate these sections explicitly when useful:
   - `Target design`
   - `Current implementation`
   - `Implementation status`
   - `Known deviation`
   - `Not yet implemented`
   - `Architectural risk`
5. Update `docs/architecture/implementation-gap-analysis.md` when drift is found.
6. Run the repo's available verification commands after documentation edits when practical.

## Source Priority

Use source code as the source of truth for current behavior.

Use target-design documents as the source of truth for intended behavior, in this order when available:

1. `first-class-object.txt`
2. `user-agent-workflow.txt`
3. `src/agents/planner/nodes.py`
4. `memory.txt`
5. `src/agents/planner/graph.png`
6. existing repo files for actual commands, modules, APIs, package names, and current behavior

If target design and code conflict, document the conflict. Do not silently reconcile it.

## Documentation Guardrails

- Do not turn design documents into false implementation claims.
- Do not turn generated summaries into architectural truth.
- Do not invent setup commands, test commands, package managers, services, database choices, API endpoints, or directories.
- Update `README.md` only with verified commands and implemented features.
- Update `AGENTS.md` when target invariants change.
- Preserve CogniEDA's epistemic boundaries: FCO, workflow state, provenance, cache, filesystem artifact, and generated view are different layers.

## Target FCO Invariants

Only these are target FCOs:

- `Objective`
- `DataProfile`
- `Assumption`
- `Task`
- `Hypothesis`
- `Evidence`
- `Discovery`
- `SessionFrame`

Do not describe `Workspace`, `Question`, `AnalysisFrame`, `GeneratedView`, `PlannerOperation`, `ExecutionRun`, or `EvidenceCacheEntry` as FCOs unless the project owner explicitly changes the design.

## Completion Report

When finishing a documentation task, report:

- files created or changed
- documentation structure produced
- implementation gaps found
- design/code mismatches found
- commands run and results
- docs requiring project-owner review
- unresolved architectural decisions
