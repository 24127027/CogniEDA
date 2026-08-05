# Validity

Validity answers whether recorded state remains eligible for a particular
current use. It protects present reasoning without erasing the durable account
of what was observed, proposed, admitted, or decided earlier.

```text
historical truth-to-record
  !=
current-use eligibility
```

A record can remain historically accurate while becoming invalid,
superseded, stale, restricted, conflicted, or otherwise ineligible for a
protected use. Conversely, a record that is topically relevant or confidently
worded is not necessarily valid for that use.

This track defines the **target design**. It does not freeze a validity-event
wire schema or claim that the complete model is implemented today.

## What validity is not

Validity is not:

- deletion or history rewriting;
- a popularity score;
- model confidence;
- retrieval relevance;
- a generic boolean detached from scope, lineage, and permitted use;
- permission to treat a planning record as scientific support.

Validity is a governed determination over typed state. It asks which object or
record is being considered, under which Objective and scientific lineage, for
which scope and purpose, at which lifecycle point, and under which current
constraints.

## The validity model

CogniEDA preserves three related but distinct things:

| Concern | Question | Consequence |
| --- | --- | --- |
| historical record | What happened and what was admitted at the time? | remains inspectable under authorization |
| validity state | What explicit event changed eligibility, why, and under whose authority? | is durable, attributable, and traceable |
| current-use decision | May this exact state be used now for this purpose and scope? | admits, restricts, flags, or excludes the state |

An invalidation may exclude Evidence from protected evaluation while leaving
the original observed payload unchanged. A superseded DataProfile may still
explain an earlier analysis while no longer being the active data state for a
new investigation. A Discovery may require review because supporting Evidence
changed without being automatically rewritten or deleted.

## Typed validity flow

Validity follows admitted relationships rather than arbitrary graph reach:

```text
DataProfile
  -> ExecutionRun / AnalysisFrame
  -> Evidence
  -> EvaluationBundle
  -> DiscoveryProposal
  -> Discovery
  -> SessionFrame / GeneratedView eligibility
```

Every arrow is conditional. Propagation depends on relationship type, affected
contract, scope, lifecycle, validity-event class, current use, and protected-
evaluation rules. It does not imply that all descendants receive the same
status or that the semantic Knowledge Graph contains every record shown.

## Validity and authority

An authorized validity boundary decides whether a validity transition is
permitted. Application authority applies the exact transition, preserves its
attribution and lineage, and enforces downstream eligibility. Neither an agent
nor a retrieval score may silently change validity.

Validity review also preserves the scientific authority split:

- Data Explorer returns bounded observations; it does not decide the validity
  of a claim.
- Hypothesis Analyst performs protected evaluation over eligible admitted
  inputs; it does not grant those inputs durable eligibility.
- Graph Miner may locate validity relations and conflicts read-only; it cannot
  mutate state or admit a cross-Objective relation.
- governance may authorize review outcomes without rewriting scientific
  content.
- application authority admits validity transitions without inventing
  scientific meaning.

## Continue reading

- [Validity over time](validity-over-time.md) owns historical truth, current
  authority, explicit validity events, correction, supersession, and scope
  changes.
- [Validity propagation](validity-propagation.md) owns typed downstream
  eligibility, protected-use exclusion, review, restoration, and GeneratedView
  staleness.
- [Context](../context/index.md) explains how a current operation selects only
  the state eligible for its reasoning mode.

## Implementation status

**Partially implemented.** Current source preserves immutable DataProfile and
Evidence payloads, supports DataProfile and Evidence supersession, supports
Evidence invalidation, and can flag or historically scope some dependent
Evidence and Discovery records. The current context policy excludes
superseded or invalidated Evidence from protected synthesis projections.

The complete target is not implemented. There is no general durable validity-
event model, contract-complete propagation through the scientific lifecycle,
authorized restoration workflow, or end-to-end current-use eligibility
service.
