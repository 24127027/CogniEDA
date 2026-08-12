# MVP-v2: minimum complete scientific research loop

## Purpose and authority

This page is the single normative definition of **MVP-v2**. MVP-v2 is the
minimum complete scientific research loop for CogniEDA. It is a **Design
target**, not a claim that the loop is implemented on current `main`.

The earlier definition of MVP as a small executable path containing Planner,
Data Explorer, direct Task-to-Evidence admission, and an in-memory
`SessionFrame` is superseded by this page. That bounded path remains useful
current implementation evidence, but it is not the MVP-v2 target and does not
move canonical scientific, governance, graph, or restart behavior beyond MVP.

Keep these three levels separate:

| Level | Owner | Meaning |
| --- | --- | --- |
| canonical architecture | [System overview](system-overview.md) and canonical concept owners | the complete long-term authority and research-state model |
| MVP-v2 | this page | the minimum complete subset of the canonical architecture that must work end to end |
| current implementation | [Current state](../status/current-state.md) | dated, source- and test-qualified behavior that exists now |

## Product thesis and priorities

CogniEDA is validity-preserving research-state infrastructure for
multi-session data investigation. It is not merely an EDA chatbot.

MVP-v2 decisions follow this priority order:

1. conclusion validity and traceability;
2. context type safety;
3. multi-session continuity;
4. speed and convenience.

Missing authority, identity, lineage, scope, validity, admission state, or
contract version fails closed. Conversation, model output, planning support,
retrieval relevance, and cached results do not become scientific authority by
being useful or available.

## Definition of Done

MVP-v2 is complete only when one supported end-to-end workflow demonstrates:

```text
Workspace
  -> dataset adopted
  -> active DataProfile
  -> Human request through Planner
  -> Objective
  -> approved and active PlanRevision
  -> eligible leaf SCIENTIFIC Task
  -> Hypothesis Analyst feasibility
  -> exactly one Hypothesis for the feasible Task
  -> locked InvestigationProtocol
  -> one or more bounded EvidenceRequests
  -> Data Explorer deterministic execution
  -> ExecutionRun and AnalysisFrame provenance
  -> authoritative Evidence admission
  -> Hypothesis Analyst protected evaluation
  -> typed scientific outcome
  -> DiscoveryProposal when the outcome is eligible
  -> GovernanceDecision
  -> Discovery admission when approved
  -> semantic Knowledge Graph updated and queryable
  -> Planner response
  -> process restart
  -> authoritative state restored
  -> follow-up uses retained eligible research state correctly
```

The workflow may validly stop at a typed non-Discovery outcome. Completion
does not require fabricating a Hypothesis, Evidence, or Discovery when its
admission conditions are not met. The demonstrated happy path must nevertheless
include one governance-approved Discovery so the complete authority chain,
semantic graph projection, restart, and follow-up behavior are exercised.

## Required canonical research chain

MVP-v2 implements a narrow but real instance of the canonical chain:

```text
Objective
  -> PlanRevision
  -> Task
  -> ScientificInvestigationRun
  -> Hypothesis
  -> InvestigationPlan / InvestigationProtocol
  -> EvidenceRequest
  -> ExecutionRun
  -> AnalysisFrame
  -> Evidence
  -> EvaluationBundle
  -> DiscoveryProposal
  -> GovernanceDecision
  -> Discovery
  -> GeneratedView
```

These records are not interchangeable. In particular:

```text
proposal != approval
execution output != Evidence
evaluation outcome != Discovery
SessionFrame membership != operation context eligibility
conversation != research authority
```

Application/domain authority validates and admits durable state at the
required transitions. A controlled admission may occur within one logical
Planner interaction when the admitted object is required by the next step; it
need not be postponed until the entire interaction ends.

## Fixed object and graph boundaries

The FCO set is exactly:

```text
Objective
DataProfile
Assumption
Task
Hypothesis
Evidence
Discovery
SessionFrame
```

The semantic Knowledge Graph contains exactly:

```text
Objective
Hypothesis
Evidence
Discovery
```

`PlanRevision`, `ScientificInvestigationRun`, `InvestigationPlan`,
`InvestigationProtocol`, `EvidenceRequest`, `ExecutionRun`, `AnalysisFrame`,
`EvaluationBundle`, `DiscoveryProposal`, `GovernanceDecision`,
`GeneratedView`, and recovery records are important non-FCO state. They do
not become semantic graph nodes merely because MVP-v2 requires them.

## Planning and Task requirements

Planning is an active, approval-bound loop:

```text
user request
  -> Planner determines whether project work is required
     -> no: answer directly from eligible retained state
     -> yes: draft a high-level plan
        -> gaps identified
        -> bounded Graph Miner or Data Explorer planning support when needed
        -> candidate PlanRevision revised
        -> application validates candidate without persistence
        -> Human reviews and approves exact candidate
        -> application validates exact approved candidate again
        -> immutable PlanRevision persisted and activated
        -> eligible Task DAG work executes
```

Planning-support observations are not Evidence. `PlanRevision` represents the
full approved Task DAG. A Task is an independently governed semantic work
unit; required capability is not Task semantics. Exactly one immutable
`PlanTaskBinding` represents each member Task and owns required capability,
non-negative `order_rank`, and finite `LOW`, `NORMAL`, or `HIGH` priority.
Membership is derived from the bindings;
dependencies remain explicit DAG edges. Related workflow-lifecycle state owns
approval and activation metadata.

An unapproved candidate is not durable authoritative PlanRevision state.
Validation alone is not admission; persistence and activation belong to the
later exact-approval transition.

The DAG alone determines eligibility. Rank ties are valid for concurrent or
independent Tasks, canonical Task-ID ordering is only a deterministic
serialization tie-breaker, and neither rank nor priority overrides a
dependency. A binding coordination change changes PlanRevision content and its
fingerprint without, by itself, creating a successor Task.

Capability is execution/dispatch-owned. PlanRevision states the requirement;
`ExecutorRegistry` resolves a concrete runtime provider. Role, provider,
worker, process, model, and Planner identity are excluded from plan content and
its fingerprint. Planner coordinates but is not a Task executor. When retained
authoritative state already answers a request, Planner synthesizes the response
without creating a Task, capability, or provider path.

PlanRevision and its bindings contain no concrete DataProfile identity or data
selection. Planner describes intended data scope only through Task semantics.
Each specialist or controller receives complete authoritative DataProfile
context and chooses the concrete applicable profile and scope within its own
authority. Exact DataProfiles actually used are captured later in execution or
scientific provenance and are not PlanRevision fingerprint content.

The immutable PlanRevision content does not embed configurable stopping
conditions, replan triggers, or hypothetical future causes. Plan-execution
completion, interruption, approval and activation state, and replanning are
workflow-lifecycle state associated with the revision. Scientific stopping is
owned by `InvestigationProtocol`; bounded execution stopping is owned by the
applicable role-native work order.

Canonical Task kinds are exactly:

```text
DATA
SCIENTIFIC
GRAPH
```

New authoritative state accepts only canonical Task meanings; legacy shapes do
not become fallback authority. A semantic Task change creates a successor
identity. A coordination-only change belongs in a PlanRevision. Proposed Tasks
cannot execute.

Only an eligible feasible leaf `SCIENTIFIC` Task may enter scientific
investigation. A feasible leaf produces exactly one Hypothesis; an infeasible
or otherwise ineligible Task produces none and ends with a typed outcome. A
parent Task produces neither a Hypothesis nor a Discovery.

## Authority boundaries

The Human communicates only with Planner. Planner is the control plane and
owns Objective interaction, high-level planning, PlanRevision coordination,
Task DAG decomposition, routing, replanning, session coordination,
GeneratedViews, and the Human approval boundary.

Planner does not author scientific feasibility, Hypotheses, methods,
parameters, decision rules, random seeds, variable bindings, protocols,
Evidence obligations, protected evaluation, or DiscoveryProposal content. It
does not directly access datasets or admit Evidence or Discovery.

Data Explorer is the exclusive dataset operator. It performs authorized,
bounded profiling, inspection, transformation, and deterministic analysis. It
returns observations and provenance material; it does not scientifically
evaluate a Hypothesis or admit Evidence or Discovery.

Hypothesis Analyst is the scientific investigation controller. It owns
feasibility, Hypothesis formalization, InvestigationPlan,
InvestigationProtocol, Evidence obligations, diagnostics, robustness,
falsification, contradiction handling, stopping rules, protected evaluation,
and exact DiscoveryProposal content. It may issue multiple bounded
EvidenceRequests but never accesses datasets directly or admits a Discovery.

Graph Miner is read-only over Objective, Hypothesis, Evidence, and Discovery.
It may return typed references, paths, gaps, conflicts, and validity
information. It does not access datasets, mutate the graph or SessionFrame,
perform governance, or admit semantic state.

Governance approves, rejects, holds, or requests correction, more Evidence,
or conflict review without rewriting scientific content. Application/domain
authority owns identity, validation, admission, persistence, atomic
transitions, validity propagation, replay safety, and fail-closed enforcement.

## Assumption quarantine and protected evaluation

An Assumption is planning state or a planning constraint. It is not Evidence
and cannot enter protected evaluation or Discovery support as an inference
premise. If a user-provided Assumption is reasonably testable, Planner warns
and proposes a `SCIENTIFIC` Task. Otherwise it remains planning state.

Protected evaluation belongs to Hypothesis Analyst and consumes only a closed,
validated `EvaluationBundle` containing the applicable Hypothesis, locked
protocol and authorized revisions, admitted Evidence, ExecutionRun and
AnalysisFrame lineage, precommitted decision rules, diagnostics, uncertainty,
robustness, falsification, and stopping state.

Scientific support excludes raw conversation, planning Assumptions, Planner
opinion, unadmitted Data Explorer output, arbitrary retrieval, unrelated prior
Discoveries, and caches whose authority and validity have not been established.

## Scientific outcomes and Discovery eligibility

A Hypothesis produces at most one Discovery. The eligible outcome classes are:

```text
SUPPORTED
CONTRADICTED
VALUABLE_INCONCLUSIVE
```

`VALUABLE_INCONCLUSIVE` requires protocol completion or governed stopping,
genuine added knowledge, a narrowly scoped claim, and wording that does not
assert absence merely because Evidence was weak. Every durable Discovery
requires a GovernanceDecision and application-authority admission.

Typed non-Discovery endings include:

```text
NOT_TESTABLE
INSUFFICIENT_DATA
INSUFFICIENT_EVIDENCE
PROTOCOL_EXHAUSTED
OUT_OF_SCOPE
CANCELLED
INVALIDATED
SUPERSEDED
CANCELLED_BY_REPLAN
```

Fail-to-reject and inconclusive results must not be strengthened into absence
claims. A safe form is: “available evidence is insufficient to reject
independence within scope S using method M on DataProfile V.”

## Dataset and Evidence requirements

Raw or admitted dataset states are immutable. Cleaning or transformation that
changes data creates successor dataset state and a successor DataProfile with
explicit lineage. External dataset admission and active DataProfile switching
are authority-sensitive; filesystem presence alone grants neither.

Canonical scientific Evidence must follow:

```text
SCIENTIFIC Task
  -> ScientificInvestigationRun
  -> Hypothesis
  -> locked InvestigationProtocol
  -> EvidenceRequest
  -> DataWorkOrder
  -> ExecutionRun
  -> AnalysisFrame
  -> Evidence admission
```

Evidence admission verifies exact identity, Objective and DataProfile scope,
protocol and request binding, executed capability, role-native output,
provenance, contract version, and current-use eligibility. Missing or
mismatched lineage creates zero Evidence.

## SessionFrame, context, and conversation

In the canonical MVP-v2 direction, SessionFrame is structured
research-session membership and state. It tracks authoritative references
such as Objective, Assumption, Task, DataProfile, and Evidence identities, the
active Objective and DataProfile, and supported Hypothesis or Discovery
references where appropriate.

Three boundaries remain distinct:

```text
historically referenced by SessionFrame
  != selected into an operation-specific context
  != authorized as scientific support
```

Referenced dependencies do not automatically become SessionFrame membership.
Operation-specific planning, answer, scientific-control, evaluation, graph,
and recovery contexts apply their own purpose, scope, authority, lifecycle,
validity, and lineage rules.

Conversation is a non-authoritative continuity surface. Native provider
history may be retained to preserve coherent model interaction, but raw chat
does not become SessionFrame membership, Evidence, protected-evaluation input,
or recovery authority. MVP-v2 restart succeeds from durable typed state, not
by asking a model to reconstruct authority from a transcript.

## Workspace, sessions, and cross-Objective behavior

One Workspace may contain multiple Objectives. Different sessions may proceed
concurrently when bound to different Objectives. During the current
architecture phase, at most one active Planner session may coordinate a given
Objective. This is not a one-active-Objective-per-Workspace rule.

Generic cross-Objective relation admission is not active. Related Objectives
may motivate an inert composite-Objective proposal, but creation requires
Human approval and no automatic aggregation occurs.

Cross-Objective Evidence reuse requires explicit
`CrossObjectiveEvidenceReuseAdmission` and exact equality over the versioned
canonical typed obligation and lineage representations. Similarity, model
judgment, shared Workspace membership, or graph proximity grants no authority.

Canonicalization is structural only: finite typed validation, deterministic
ordering, duplicate rejection, fixed serialization, schema-version binding,
and digest computation. It does not infer synonyms, units, variable mappings,
method compatibility, scope containment, or semantic equivalence.

## Approval modes

MVP-v2 supports the canonical Human-boundary modes:

```text
ALWAYS_ASK
POLICY_GUARDED  (default)
ALWAYS_ACCEPT
```

An approval mode never overrides validity, lineage, authority, or
traceability.

## Retrieval staging

Retrieval evolves only after authority and durable state make it useful:

| Capability | MVP-v2 relationship |
| --- | --- |
| deterministic bounded typed context | required |
| session-local typed retrieval after meaningful durable history exists | optional unless the MVP-v2 demonstration needs it |
| semantic inquiry through Graph Miner and the semantic Knowledge Graph | required for the bounded graph-query portion of the MVP-v2 demonstration |
| embeddings or hybrid ranking justified by evaluation | **Deferred** beyond MVP-v2 |

Every stage applies authority, scope, lifecycle, validity, and lineage filters
before relevance ranking. Embeddings are not an MVP-v2 requirement.

## Explicit non-goals

MVP-v2 does not require:

- embeddings or hybrid retrieval;
- generic cross-Objective relations or automatic Objective aggregation;
- more than one active Planner session for the same Objective;
- arbitrary generated Python or unbounded dataset execution;
- a production UI, public service API, deployment platform, or supported
  product CLI;
- distributed scale, generalized multi-database support, or performance work
  that weakens validity and traceability.

These are non-goals of the minimum demonstration, not permission to violate
the canonical authority model.

## Current transitional foundation

**Partially implemented.** Current `main` provides valuable bounded
foundations: typed research-state values, bounded Planner behavior,
deterministic Data Explorer execution and direct Evidence admission, in-process
conversation continuity, multi-provider model configuration, SQLite
persistence seams, and execution infrastructure.

The current direct path is transitional:

```text
Task -> Data Explorer -> Evidence
```

It is not canonical scientific Evidence lineage and does not satisfy MVP-v2.
The complete loop still requires the real scientific investigation, protocol,
request, execution, AnalysisFrame, protected evaluation, governance,
Discovery, semantic graph, and restart boundaries. See
[Current state](../status/current-state.md) for the exact dated boundary.

## What the MVP-v2 demonstration must show

The product capability is demonstrated only when a reader can trace and
observe, at minimum:

- one real dataset is explicitly adopted and bound to an active DataProfile;
- one Human request passes only through Planner;
- one full approved PlanRevision and Task DAG is retained;
- only an eligible feasible leaf `SCIENTIFIC` Task creates one Hypothesis;
- the protocol is locked before Evidence-producing execution;
- Data Explorer alone reads the dataset and executes deterministic work;
- failed, blocked, invalid, or mismatched work creates zero Evidence;
- admitted Evidence retains the complete canonical scientific and execution
  lineage;
- protected evaluation excludes conversation and Assumptions;
- a Discovery-eligible outcome receives governance and exact admission;
- a non-Discovery outcome remains typed without a fabricated claim;
- the semantic graph exposes only Objective, Hypothesis, Evidence, and
  Discovery;
- process restart restores authoritative state and permitted next actions;
- follow-up uses retained eligible research state rather than transcript
  reconstruction;
- Objective isolation and one-active-Planner-session-per-Objective enforcement
  fail closed;
- no approval mode bypasses authority, validity, lineage, or traceability.
