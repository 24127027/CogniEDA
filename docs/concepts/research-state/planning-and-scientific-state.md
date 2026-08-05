# Planning and scientific state

Planning decides what work should be considered. Scientific state records what
was committed for investigation, what was observed, and what an admitted claim
may say. CogniEDA keeps these responsibilities separate so that useful planning
material cannot silently become scientific support.

## Objective establishes scope

An `Objective` is the root research scope. It defines what an investigation
seeks to establish and bounds planning, scientific work, retrieval, and
governance.

A `Workspace` may contain multiple concurrently active Objectives. Sessions may
work concurrently when they are bound to different Objectives. In the current
architectural phase, at most one active Planner session is allowed per
Objective. One Task or Hypothesis does not directly belong to multiple
Objectives.

## Assumptions guide planning only

An `Assumption` records a provisional planning constraint. It may originate in
user input about data, domain context, or research conditions. It is not
Evidence and cannot serve as an inference premise in protected evaluation.

When a proposed assumption can reasonably be tested with available or
obtainable data, the Planner should flag that distinction and propose
scientific work. Labeling a testable claim as an Assumption must not become a
shortcut around Evidence.

After a Discovery exists, it may be compared with Assumptions to flag a
possible contradiction. That flag is a review signal, not an automatic rewrite
or deletion of either object.

## Task is work; PlanRevision is a plan

A `Task` is a durable semantic work unit. Its canonical kinds are:

```text
DATA
SCIENTIFIC
GRAPH
SYNTHESIS
```

The semantic work defines Task identity. Priority, ordering, assignment,
dependencies, scheduling, and presentation metadata do not. Those concerns
belong to `PlanRevision` and related non-FCO records.

A PlanRevision represents an entire approved or proposed plan version: Task DAG
membership, dependencies, executor assignment, DataProfile references,
stopping conditions, replan triggers, approval state, and a plan fingerprint or
equivalent identity. Users discuss changes with the Planner rather than editing
Tasks inside an approved PlanRevision directly. A bounded amendment creates a
successor PlanRevision; a sufficiently large change returns to a grounded
planning loop.

## Planner coordinates but does not operationalize science

The Planner is the sole human-facing agent boundary. At this conceptual level,
it coordinates Objectives, PlanRevisions, Task DAG proposals, routing,
replanning, SessionFrames, GeneratedViews, and approval policy.

It does not scientifically operationalize a Hypothesis. It does not own the
method, parameters, decision rule, seed, variable bindings, or scientific
protocol. It also does not directly create authoritative Evidence or
Discovery. Planner output crosses typed proposal and application-authority
boundaries before durable change occurs.

## Eligibility for scientific investigation

Only an eligible feasible leaf `SCIENTIFIC` Task can produce a Hypothesis. A
parent Task produces neither a Hypothesis nor a Discovery. A proposed Task
cannot execute.

The Hypothesis Analyst owns feasibility and scientific operationalization. For
an eligible feasible leaf Task, it may create at most one `Hypothesis` through
the scientific investigation lineage. The Hypothesis is a scientific
commitment, not an observed result and not a conclusion.

The scientific investigation may use an `InvestigationPlan`,
`InvestigationProtocol`, protocol revisions, and repeated `EvidenceRequest`
records. These are durable non-FCO investigation records. They preserve how the
scientific commitment is tested without becoming epistemic graph nodes.

## Observation, Evidence, and provenance

Data Explorer is the specialist that exclusively accesses datasets. It
performs bounded data work and can return observations, diagnostics, artifacts,
and `AnalysisFrame` material. It does not evaluate Hypotheses, create
Discoveries, or own authoritative persistence.

An observation becomes `Evidence` only through application-authority admission
against the scientific and provenance contracts. Evidence is therefore more
than raw tool output or prose: it is an immutable, observation-backed record
bound to its Hypothesis, DataProfile, AnalysisFrame, ExecutionRun, method, and
necessary provenance.

## Protected evaluation and outcomes

Protected final evaluation belongs to the Hypothesis Analyst or scientific
investigation controller. It is an authority-bounded scientific act, not a
separate canonical Evaluator agent. The evaluation context is constructed from
the Hypothesis, DataProfile, AnalysisFrame provenance, admitted Evidence,
method metadata, parameters, decision rule, uncertainty, validity basis, and
necessary provenance.

The context excludes Assumptions and existing Discoveries. It also excludes
raw chat history, failed reasoning chains, rejected Tasks, and unverified
GeneratedViews by default. The schema of the protected input, not topical
similarity, enforces the boundary.

Evaluation can produce a `DiscoveryProposal` or a typed non-completion. A
proposal is not yet a Discovery. Governance may approve, reject, or hold an
eligible proposal and may request correction, additional Evidence, or conflict
review. Governance does not revise scientific content; the appropriate
scientific authority creates any revised proposal. Application authority
validates and applies only the authorized transition.

## Discovery is conditional, not automatic

Discovery eligibility is limited to:

```text
SUPPORTED
CONTRADICTED
VALUABLE_INCONCLUSIVE
```

`VALUABLE_INCONCLUSIVE` requires a completed protocol, a clearly valuable
inconclusive outcome, a narrowly bounded claim, a DiscoveryProposal,
governance, and authoritative admission. An inconclusive result without those
conditions remains a typed non-Discovery outcome.

Non-Discovery endings include `NOT_TESTABLE`, `INSUFFICIENT_DATA`,
`INSUFFICIENT_EVIDENCE`, `PROTOCOL_EXHAUSTED`, `OUT_OF_SCOPE`, `CANCELLED`,
`INVALIDATED`, `SUPERSEDED`, and `CANCELLED_BY_REPLAN`. These states preserve
what happened without manufacturing a claim.

## The protected boundary in one view

| Material or act | Planning | Protected scientific evaluation | Scientific authority |
| --- | ---: | ---: | --- |
| Objective scope | yes | scope binding only | no empirical support |
| Assumption | yes | no | none |
| Task and PlanRevision | yes | no | workflow only |
| Hypothesis | used to plan investigation | yes | scientific commitment |
| admitted Evidence and provenance | may inform next work | yes | observation-backed input |
| existing Discovery | may inform planning | no | authority only within its own scope and validity |
| GeneratedView | presentation aid | no | none |
| governance decision | authorizes transition | does not evaluate | decision authority, not scientific authorship |
| application admission | applies approved change | validates boundary | persistence and transition authority |

Continue with [Identity, scope, and lineage](identity-scope-and-lineage.md), or
return to the [research-state foundation](index.md).
