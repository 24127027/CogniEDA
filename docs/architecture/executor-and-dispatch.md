# Executor and dispatch

CogniEDA specialists perform bounded work behind typed, capability-based
contracts. They are restart-safe workers, not alternate human-facing agents and
not owners of durable research state.

This page defines the target specialist and dispatch architecture. It avoids
freezing exact serialization schemas; the named contracts define semantic and
authority boundaries.

## Common executor boundary

Every specialist invocation has the same operational posture:

1. application coordination receives an admitted work identity;
2. the dispatcher resolves the required capability against an explicit
   registry;
3. the specialist receives only its role-native typed input and eligible
   context;
4. the specialist returns a bounded role-native result;
5. application coordination validates and normalizes the result;
6. application authority decides which durable admission or transition, if
   any, is permitted.

Executors should be stateless or restart-safe. Durable progress, leases,
attempt identity, and replay protection belong to application authority, not
to hidden in-memory agent state.

## Task kind and governed specialist boundaries

Canonical Task kinds are:

```text
DATA
SCIENTIFIC
GRAPH
```

`TaskKind` is a semantic and epistemic work class. It may constrain authority:
physical data access crosses Data Explorer, scientific operationalization and
protected evaluation cross Hypothesis Analyst, and graph inquiry remains
read-only. It is not a compile-time `TaskKind -> Capability -> Provider`
routing table.

PlanRevision and `PlanTaskBinding` contain no capability, provider, specialist,
worker, or tool selection. Application authority determines eligibility and
which governed role-level tools are available; Planner reasons over the
interactions needed to pursue the eligible Task. One Task may require zero,
one, or multiple specialist interactions. Planner response synthesis is not
Task work and does not justify a synthesis capability, Planner provider, or
Planner executor role.

Execution internals may remain capability-based and must fail closed when an
allowed role-level interaction cannot be fulfilled. They must not fall back to
a legacy executor, reinterpret Task meaning, or expose internal provider
routing as approved plan content.

Neither PlanRevision nor `PlanTaskBinding` selects a concrete DataProfile.
Specialists receive the complete authoritative DataProfile context available
for their work, then select the applicable profile and concrete scope within
their role-native authority. Receiving metadata does not grant Graph Miner or
Planner dataset access. Exact profiles actually used remain mandatory
downstream execution or scientific provenance.

## Role-native contracts

The canonical specialist contracts are:

```text
DataWorkOrder
  -> DataExplorerResult

ScientificInvestigationInput
  -> HypothesisAnalystResult

GraphInquiryRequest
  -> GraphInquiryResult
```

These are different contracts because the roles have different inputs,
allowed actions, outputs, and authority. A universal optional-field envelope
would create hidden authority channels and is not canonical.

### DataWorkOrder to DataExplorerResult

A `DataWorkOrder` describes a bounded direct `DATA` Task: admitted dataset
references, allowed operation, scope, resource limits, required diagnostics or
artifacts, and stopping conditions. `DataExplorerResult` returns observations,
`AnalysisFrame` material, diagnostics, artifacts, limitations, blockers, and
bounded completion status.

Those stopping conditions bound one Data Explorer execution. They are not
PlanRevision completion policy, replan triggers, or scientific investigation
stopping conditions.

This direct path is not a scientific `EvidenceRequest`. It may produce useful
observations and views without creating Evidence or a Discovery.

### ScientificInvestigationInput to HypothesisAnalystResult

`ScientificInvestigationInput` binds an eligible feasible leaf `SCIENTIFIC`
Task to the scientific-investigation state available to Hypothesis Analyst.
The result may contain feasibility, Hypothesis and protocol proposals,
EvidenceRequests, protocol revisions, a protected evaluation,
`DiscoveryProposal`, or a typed non-completion.

Hypothesis Analyst never receives dataset access. An EvidenceRequest is sent by
application coordination to Data Explorer, and the resulting observation must
pass Evidence admission before it can enter protected evaluation.

### GraphInquiryRequest to GraphInquiryResult

A `GraphInquiryRequest` bounds a read-only research-state question by Objective,
eligible object types, scope, validity posture, and traversal limits.
`GraphInquiryResult` may contain object references, graph paths,
contradictions, gaps, validity information, dependencies, related Objective
suggestions, limitations, and blockers.

The result cannot mutate the graph, admit a cross-Objective relation, or create
Evidence or Discovery.

## Data Explorer

Data Explorer has exclusive dataset access. It operates in two conceptual
modes:

| Mode | Initiator and purpose | Scientific consequence |
| --- | --- | --- |
| Direct `DataTask` | an approved `DATA` Task requests bounded data work | produces observations, diagnostics, AnalysisFrame material, artifacts, or a typed ending; not automatically Evidence |
| Scientific `EvidenceRequest` | Hypothesis Analyst requests an observation required by an InvestigationProtocol | produces bounded observation material that may become Evidence only after application-authority admission |

The modes must not be equated. Data Explorer does not define or evaluate the
Hypothesis, create a Discovery, govern a proposal, admit Evidence, write to
persistence, or communicate with the human.

## Hypothesis Analyst

Hypothesis Analyst controls scientific feasibility and investigation. For an
eligible feasible leaf `SCIENTIFIC` Task it owns exactly one Hypothesis, the
InvestigationPlan, InvestigationProtocol, Evidence obligations, repeated
EvidenceRequest construction, governed protocol revision, and protected final
evaluation. It returns a `DiscoveryProposal` or typed non-completion.

It has no dataset access, cannot bypass Data Explorer, cannot persist
authoritatively, cannot self-govern, and does not communicate with the human.
No separate peer Evaluator agent is introduced.

## Graph Miner

Graph Miner performs read-only inquiry over eligible research state. It may
support a planning consultation or an approved leaf `GRAPH` Task. It cannot
mutate graph state, perform dataset operations, create Evidence or Discovery,
govern proposals, admit cross-Objective relations, or communicate with the
human.

## Capability registry and dispatcher

The capability registry is the authoritative runtime mapping from stable
capability identity to a provider factory. Provider registration, instance
reuse, availability, and implementation identity remain outside PlanRevision
content and its fingerprint.

The dispatcher accepts an admitted work identity and an execution-internal
capability selected behind a governed role-level tool boundary. It does not
derive that value from PlanRevision or infer scientific intent from Task kind.
It verifies capability availability, contract compatibility, attempt identity,
and policy before invoking a worker.

```mermaid
flowchart LR
    T[Governed role-level tool request] --> R[Internal capability]
    R --> D{Dispatcher lookup}
    D -->|available and eligible| E[Role-native specialist]
    D -->|absent or ineligible| B[Typed blocked outcome]
    E --> N[Validated native result]
    N --> O[PlannerWorkOutcome normalization]
```

Unknown capability, missing registration, incompatible contract, or stale
attempt identity all fail closed.

## PlannerWorkOutcome normalization

The Planner does not consume arbitrary specialist-native output directly.
Application coordination validates the native result and normalizes the
Planner-facing subset into `PlannerWorkOutcome`.

Conceptual fields include source role, Task identifier, work identifier,
status, semantic summary, authoritative references, limitations, blockers,
permitted next actions, and result digest.

Normalization is projection, not authorship. It preserves authoritative
references and limitations while excluding specialist-private or
context-ineligible material. The target deliberately does not freeze field names,
wire format, or serialization details.

## Implementation status

**Partially implemented.** At the S0 library boundary, one lightweight
execution-owned `Capability` `StrEnum` drives an explicit `Capability -> ProviderFactory`
registry. One dependency-aware factory may serve multiple capabilities and its
provider instance is reused. Duplicate and absent registrations fail closed.
The thin async dispatcher invokes the resolved provider and preserves provider
failure as a controlled error.

The current PydanticAI adapter exposes a typed data-capability request through
Planner dependencies. Focused tests validate adapter to dispatcher to
registered-provider invocation without a model endpoint. Bootstrap explicitly
composes a registry, Data Explorer provider factory, dispatcher, and
`PlannerDeps`; availability no longer depends on executor module import order.

`ExecutionResult` now contains only shared transport metadata.
`DataExplorerResult` and the deferred `HypothesisAnalystResult` own their
role-native fields. A minimal `PlannerWorkOutcome` projection seam consumes
only shared metadata; full Planner consumption remains **Deferred**.

At the bounded M3-A direct-DATA library surface, an execution-internal
`DATA_ANALYSIS` request reaches Data Explorer outside PlanRevision. This
transitional plumbing is not a canonical Task-kind route. Data Explorer owns
the typed `Task.instruction -> DataAnalysisPlan` translation through its
`DataAnalysisPlannerPort`, using the application-supplied authoritative
DataProfile projection from `DataExplorerInput` and the finite
supported-operation set. Deterministic code
then validates exact columns and bounded parameters before execution. The
role-specific `DataAnalysisPlan`, `DataAnalysisOperation`, and
`CorrelationMethod` contracts live under `agents.data_explorer`; the generic
`execution` package does not define or import them.

Data Explorer is registered for `DATA_ANALYSIS`, `DATA_PROFILING`, and
`DATA_TRANSFORMATION`. The first two have a bounded donor implementation when
given the active M1-A Task instruction, authoritative DataProfile projection,
and a local dataset path. Profiling
returns the typed M1-A DataProfile through a Data Explorer-owned tool boundary
and pure deterministic computation. It does not drop duplicate rows, all-null
rows, or missing values and does not mutate the active frame. Transformation
returns a typed blocked result until it can create a successor dataset and
DataProfile; it never establishes in-place mutation as valid behavior.

Canonical `DataWorkOrder`, `ScientificInvestigationInput`,
`GraphInquiryRequest`, and complete role-native admission contracts remain
**Unsupported**. Hypothesis Analyst and Graph Miner remain unregistered runtime
scaffolds. Full Planner-to-real-dataset-to-Evidence-to-Planner execution is
also **Unsupported**.

See [MVP-v2](mvp-runtime-subset.md) for the minimum complete scientific loop
and [Persistence and admission](persistence-and-admission.md)
for the canonical durable boundary around attempts and results.
