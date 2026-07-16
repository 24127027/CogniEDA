# CogniEDA Agent Guide

CogniEDA is a governed research-state system for analytical investigation. Do not treat this project as a generic chat-memory, notebook, or vector-retrieval app.

Your highest priority is epistemic correctness: every conclusion must remain traceable, valid within scope, and protected from the wrong kind of memory entering reasoning.

## Source Of Truth

- Use source code as the source of truth for what currently exists.
- Use `first-class-object.txt` as the canonical target architecture when available.
- Use `user-agent-workflow.txt` as the target user-facing workflow when available.
- Use `src/agents/planner/nodes.py` and `src/agents/planner/graph.py` for current planner scaffolding and intended node names.
- If design docs and code conflict, document the conflict. Do not silently resolve it.

## Current Implementation Warning

The local schema and persistence layer use the target FCO names. Minimal durable `PlannerOperation`, `AnalysisFrame`, `ExecutionRun`, execution approval/outbox/inbox, and scientific-finalization paths now exist. Configured request understanding and `/manage_task` Task-proposal approval work, but several product/runtime pieces remain scaffold-level: answer/suggest/plan planner branches are incomplete, concrete executor graphs and executable DVC integration are not implemented, cache persistence is absent, and no production CLI/service/worker bootstrap exists.

## Target FCO Set

Only these are target First-Class Objects:

- `Objective`
- `DataProfile`
- `Assumption`
- `Task`
- `Hypothesis`
- `Evidence`
- `Discovery`
- `SessionFrame`

Do not introduce these as FCOs unless explicitly instructed by the project owner:

- `Workspace`
- `Question`
- `AnalysisFrame`
- `GeneratedView`
- `PlannerOperation`
- `ExecutionRun`
- `EvidenceCacheEntry`

## Target Non-FCO Boundaries

- `Workspace` is a filesystem/runtime boundary, not an FCO.
- `Question` is UI input that becomes a `Task`, not an FCO.
- `AnalysisFrame` is provenance/data-view, not an FCO.
- `GeneratedView` is runtime/provenance output, not `Discovery`.
- `PlannerOperation` is pending mutation, not an FCO.
- `ExecutionRun` is provenance, not an FCO.
- `EvidenceCacheEntry` is cache, not an FCO.

## Target Invariants

- `DataProfile` is immutable.
- `Evidence` is immutable.
- `Discovery` cannot exist without `Evidence`.
- `Discovery` must have structured `claim`, `scope`, and `validity_basis`.
- `Assumption` may guide planning but must be excluded from Conclusion/Discovery Synthesis Context.
- Proposed `Task`s cannot execute.
- Only active terminal analytical `Task`s can generate `Hypothesis` objects.
- One terminal analytical `Task` generates exactly one `Hypothesis`.
- One `Hypothesis` produces exactly one `Discovery`.
- Parent `Task`s do not produce `Discovery` objects.
- Planner nodes produce operations; `commit` persists approved operations atomically.

## Epistemic Discipline

- Keep research intent, workflow state, data state, assumptions, hypothesis/test contracts, observed evidence, evidence-bound discoveries, active context, provenance, and cache separate.
- A `Task` is workflow state, not scientific knowledge.
- `Evidence` is observed analytical result, not interpretation.
- `Discovery` is an evidence-bound claim, not a paragraph summary.
- `Assumption` cannot be used as an inference premise.
- Fail-to-reject and inconclusive results still produce knowledge, but phrase them correctly.
- Do not write "there is no relationship" unless evidence supports that stronger claim.
- Prefer: "available evidence is insufficient to reject independence within scope S using method M on DataProfile V."

## Context Type Safety

Planning Context may include `Assumption` objects.

Conclusion/Discovery Synthesis Context must exclude `Assumption` objects and existing `Discovery` objects, and rely only on:

- `Hypothesis`
- `DataProfile`
- `AnalysisFrame` provenance
- `Evidence`
- method metadata
- parameters
- decision rule
- uncertainty
- validity basis
- necessary provenance

Do not retrieve rejected `Task`s, completed `Hypothesis` objects, existing `Discovery` objects, raw chat history, failed reasoning chains, or unverified `GeneratedView`s into Conclusion/Discovery Synthesis Context by default.

## Mutation And Lifecycle Rules

- If cleaning or preprocessing changes data, create a new dataset version and a new `DataProfile`. Do not overwrite an existing `DataProfile`.
- If analytical output is wrong, stale, or superseded, create new `Evidence` and mark old `Evidence` as superseded or invalidated. Do not manually edit `Evidence`.
- After `Discovery` is created, it may be compared with `Assumption` objects to flag contradiction. Do not automatically rewrite or delete `Assumption` objects.
- Flagging is not mutation of truth. It is a review signal.

## Planner Pipeline Target

Preserve this pipeline unless the project owner changes the design:

```text
understand_request
route_intent
answer_question
propose_questions
expand_plan
manage_tasks
select_task
prepare_execution
dispatch_executor
review_execution
review_conflicts
manage_objective
manage_assumptions
request_user_input
pause
process_decision
commit
```

Planner nodes should produce operations rather than directly mutating persistent graph state. The commit step should atomically persist approved operations.

## Documentation Rules

- Inspect code before editing docs.
- Label `Current implementation`, `Target design`, `Implementation status`, `Known deviation`, and `Not yet implemented` explicitly.
- Update [docs/architecture/implementation-gap-analysis.md](docs/architecture/implementation-gap-analysis.md) when drift is found.
- Do not turn design targets into false implementation claims.
- Do not treat generated summaries as architectural truth.
- Update `README.md` only with verified commands and implemented features.

## Implementation Rules

- Classify new features before implementation: FCO, workflow state, provenance, cache, filesystem artifact, or generated view.
- Default uncertain durable objects to provenance or generated view rather than promoting them into durable knowledge.
- Prefer explicit schemas, validators, lifecycle guards, and tests over informal conventions.
- Make the smallest coherent change that preserves the FCO model.
- Add or update tests for every invariant touched.

After completing a task, report what changed, which invariant was protected, what tests were run, and any unresolved architectural risk.
