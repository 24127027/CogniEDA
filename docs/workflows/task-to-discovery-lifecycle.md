# Task To Discovery Lifecycle

## Target Design

The target lifecycle is:

```text
Objective
  -> Task proposal and approval
  -> active terminal analytical Task
  -> exactly one Hypothesis
  -> execution over DataProfile and AnalysisFrame
  -> immutable Evidence
  -> exactly one Discovery
```

## Target Invariants

- Proposed Tasks cannot execute.
- Only active terminal analytical Tasks can generate Hypotheses.
- A terminal analytical Task must have no children.
- A terminal analytical Task must use an accepted DataProfile.
- A terminal analytical Task must contain one evaluable claim.
- A terminal analytical Task must have grounded variables or derivable metrics.
- A terminal analytical Task must define evidence expectation.
- One terminal analytical Task generates exactly one Hypothesis.
- One Hypothesis produces exactly one Discovery.
- Parent Tasks do not produce Discoveries.
- Parent-task answers are `GeneratedView`s over descendant Discoveries, Evidence, and provenance.

## Current Implementation

Current implementation:

- `Task` does not exist.
- `Objective` does not exist.
- `Discovery` does not exist.
- `GeneratedView` does not exist.
- `Hypothesis` exists but is not tied to a source task.
- `Evidence` exists but is not tied to a target `AnalysisFrame` or `ExecutionRun`.
- Planner nodes for task selection, execution preparation, dispatch, review, conflict review, and commit are stubs.

## Implementation Status

Design target / not implemented.

## Current Partial Support

Current `Hypothesis` and `Evidence` repositories support:

- hypothesis creation and status updates
- links from hypotheses to assumptions and datasets
- evidence creation
- typed evidence-to-hypothesis evaluation outcomes
- evidence lookup by dataset, assumption, hypothesis, and decision

This is useful scaffold behavior, but it does not enforce target lifecycle cardinality.

## Architectural Risk

If future code allows direct Hypothesis or Evidence creation without a terminal Task and without a Discovery validity envelope, the system can accumulate analytical outputs without a governed path from intent to evidence-bound knowledge.
