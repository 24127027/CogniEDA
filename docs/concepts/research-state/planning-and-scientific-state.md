# Planning and scientific state

Planning decides what governed work should be considered. Scientific state
records what was committed for investigation, what was observed, and what an
admitted claim may say. CogniEDA keeps these responsibilities separate so
planning material cannot silently become scientific support.

This page retains ownership of that planning-versus-science distinction. The
[scientific lifecycle](../scientific-lifecycle/index.md) owns the detailed
scientific sequence, contracts, outcomes, and governance.

## Objective establishes scope

An `Objective` is the root research scope. It bounds planning, scientific work,
retrieval, and governance. A Workspace may contain multiple Objectives, but a
Task or Hypothesis belongs to one Objective-scoped lineage rather than being
silently shared across Objectives.

## Assumptions guide planning only

An `Assumption` is a provisional planning constraint. It is not Evidence and
cannot serve as an inference premise in protected evaluation. A testable claim
should become proposed scientific work rather than being admitted as an
Assumption to avoid Evidence requirements.

Keeping an Assumption explicit is still useful: it records the belief or
constraint that shaped planning, makes uncertainty visible, and lets later
Evidence trigger review. Quarantine preserves that context without rewarding
an untested belief with evidential authority. If the claim cannot reasonably be
tested with available means, it may remain a planning constraint; if it can be
tested, Planner should propose a `SCIENTIFIC` Task.

After Discovery admission, comparison may flag an Assumption for review. The
flag is not an automatic rewrite or deletion of either object.

## Task is work; PlanRevision is a plan

A `Task` is a durable semantic work unit of exactly one canonical kind:

```text
DATA
SCIENTIFIC
GRAPH
SYNTHESIS
```

| Kind | Reader-facing purpose |
| --- | --- |
| `DATA` | explore, profile, or create an authorized successor data state through Data Explorer |
| `SCIENTIFIC` | govern one scientific investigation through Hypothesis Analyst |
| `GRAPH` | ask a bounded read-only question about semantic research-state relationships |
| `SYNTHESIS` | let Planner derive a GeneratedView from eligible admitted state |

A Task is an independently managed deliverable. A short planning consultation
with Data Explorer or Graph Miner is not automatically a Task; it becomes one
only when the plan needs a governed work unit with its own identity and
lifecycle.

`PlanRevision` is the non-FCO version of an entire proposed or approved Task
DAG, including membership, dependencies, assignment, ordering, approval, and
other coordination state. Those concerns do not define Task identity.

A change to Task meaning requires a successor Task. A change to the approved
plan creates an authorized successor PlanRevision or returns to grounded
planning; it does not silently edit the active plan.

## Planner coordinates but does not operationalize science

Planner owns Objective and PlanRevision coordination, Task proposals, routing,
replanning, approval interaction, SessionFrame coordination, and GeneratedView
coordination. It does not author the scientific Hypothesis, InvestigationPlan,
InvestigationProtocol, Evidence obligations, decision rule, or protected final
evaluation.

Planner proposals cross application-authority validation and admission before
durable transition. See [Scientific authority](../scientific-lifecycle/scientific-authority.md)
for the complete authority split.

## Eligibility for scientific investigation

Only an eligible feasible leaf `SCIENTIFIC` Task can source exactly one
Hypothesis. Parent, proposed, unapproved, and infeasible Tasks source none. The
canonical owner of eligibility, feasibility outcomes, investigation records,
and scientific contracts is [Scientific authority](../scientific-lifecycle/scientific-authority.md).

## Observation, Evidence, and provenance

Data Explorer has exclusive dataset access but no final scientific-evaluation
or Evidence-admission authority. The canonical EvidenceRequest, DataWorkOrder,
ExecutionRun, AnalysisFrame, observation-candidate, and Evidence-admission
sequence is defined in [Evidence and AnalysisFrames](../scientific-lifecycle/evidence-and-analysis-frames.md).

## Protected evaluation and outcomes

Protected evaluation uses a closed `EvaluationBundle` and excludes
Assumptions, prior Discoveries as inference premises, conversation, generated
summaries, rejected Tasks, failed reasoning, unverified GeneratedViews, and
unrelated cross-Objective state. Its complete input and outcome rules are
owned by [Protected evaluation](../scientific-lifecycle/protected-evaluation.md).

## Discovery is conditional, not automatic

A Hypothesis produces at most one Discovery, and many valid investigations
produce none. DiscoveryProposal, governance, correction and additional-
Evidence loops, typed non-completion, and authoritative admission are owned by
[Discovery governance](../scientific-lifecycle/discovery-governance.md).

## Implementation status

**Planning/scientific separation is partially implemented; the canonical
scientific lifecycle is a design target.** Current source contains legacy Task,
Hypothesis, Evidence, Discovery, provenance, and context-safety surfaces but
does not implement the complete lifecycle linked above.
