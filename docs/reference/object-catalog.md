# Object catalog

This catalog is a compact lookup surface. Conceptual explanations live in the
[research-state foundation](../concepts/research-state/index.md). FCO status,
semantic Knowledge Graph membership, durability, immutability, and authority
are independent properties.

## Canonical First-Class Objects

| Name | Category | In semantic graph? | Conceptual authority | Purpose and key relationship | Lifecycle posture | Full explanation |
| --- | --- | ---: | --- | --- | --- | --- |
| `Objective` | FCO; research scope | yes | Planner coordinates; application authority admits and transitions | Root scope; owns many Tasks and scientific investigations over time | lifecycle-governed | [Planning and scientific state](../concepts/research-state/planning-and-scientific-state.md#objective-establishes-scope) |
| `DataProfile` | FCO; data state | no | application authority admits | Authoritative description of one admitted data state; scientific lineage and Evidence reference it | immutable; replacement requires a new profile | [Identity, scope, and lineage](../concepts/research-state/identity-scope-and-lineage.md#dataprofile-identity-is-immutable) |
| `Assumption` | FCO; planning constraint | no | Planner coordinates; application authority admits and transitions | Guides planning only; excluded from protected evaluation | lifecycle-governed; contradiction creates a review signal | [Planning and scientific state](../concepts/research-state/planning-and-scientific-state.md#assumptions-guide-planning-only) |
| `Task` | FCO; semantic work unit | no | Planner proposes; application authority commits approved state | Represents `DATA`, `SCIENTIFIC`, `GRAPH`, or `SYNTHESIS` work within one Objective | semantic change creates a successor; lifecycle-governed | [Planning and scientific state](../concepts/research-state/planning-and-scientific-state.md#task-is-work-planrevision-is-a-plan) |
| `Hypothesis` | FCO; scientific commitment | yes | Hypothesis Analyst owns feasibility and operationalization; application authority admits | Exactly one for each eligible feasible leaf `SCIENTIFIC` Task; none for infeasible work | lifecycle-governed | [Scientific authority](../concepts/scientific-lifecycle/scientific-authority.md) |
| `Evidence` | FCO; observation-backed scientific record | yes | application authority owns admission | Binds admitted observation to Hypothesis, DataProfile, AnalysisFrame, ExecutionRun, method, and provenance | immutable; replacement uses new Evidence and lifecycle relation | [Evidence and AnalysisFrames](../concepts/scientific-lifecycle/evidence-and-analysis-frames.md) |
| `Discovery` | FCO; evidence-bound claim | yes | scientific authority authors proposal; governance authorizes; application authority admits | Scoped claim with validity basis; at most one per Hypothesis | admitted claim content remains fixed; lifecycle and validity governed | [Discovery governance](../concepts/scientific-lifecycle/discovery-governance.md) |
| `SessionFrame` | FCO; structured session membership | no | Planner coordinates membership and active selectors; application authority validates and persists | Typed research-object references plus active Objective/DataProfile selection for continuity | successor-governed membership; operation context and scientific eligibility remain separate | [SessionFrame](../concepts/context/session-frame.md) |

## Major non-FCO families

The examples are representative, not exhaustive. A non-FCO record may still be
durable, immutable, transactionally important, or authoritative within its own
boundary.

| Family | Representative records | In semantic graph? | Conceptual authority and purpose | State posture | Full explanation |
| --- | --- | ---: | --- | --- | --- |
| planning and plan versioning | `PlanRevision`, `PlanTaskBinding`, `PlanDependency`, `TaskLifecycleRecord`, `TaskPresentationMetadata`, `PlannerConsultationRun` | no | Planner proposes immutable plan content; each member Task has one binding that owns required capability, rank, and priority, while explicit edges own dependencies, `ExecutorRegistry` owns runtime provider resolution, and concrete DataProfile selection remains downstream | versioned content plus separate lifecycle-governed approval, activation, completion, interruption, and replanning state | [Task and PlanRevision](../concepts/research-state/planning-and-scientific-state.md#task-is-work-planrevision-is-a-plan) |
| scientific investigation | `ScientificInvestigationRun`, feasibility record, `InvestigationPlan`, `InvestigationProtocol`, `ProtocolRevision`, `EvidenceRequest` | no | Hypothesis Analyst or investigation controller owns feasibility, operationalization, protocol, and Evidence obligations; application authority owns durable transitions | append-oriented, versioned, or lifecycle-governed by record | [Scientific authority](../concepts/scientific-lifecycle/scientific-authority.md) |
| execution and provenance | `ExecutionRun`, `AnalysisFrame` | no | Data Explorer returns bounded work; application authority records attempt and exact data view | append-oriented provenance; attempt lifecycle governed | [Evidence and AnalysisFrames](../concepts/scientific-lifecycle/evidence-and-analysis-frames.md) |
| evaluation and outcome | `EvaluationBundle`, `ScientificInvestigationOutcome`, `DiscoveryProposal` | no | protected scientific evaluation owns interpretation and typed outcome or proposal | content-bound records; lifecycle governed where applicable | [Protected evaluation](../concepts/scientific-lifecycle/protected-evaluation.md) |
| governance and admission | `GovernanceDecision`, admission records | no | governance authorizes exact eligible proposals; application authority validates and applies transitions | append-oriented authority record | [Discovery governance](../concepts/scientific-lifecycle/discovery-governance.md) |
| validity | validity events and review signals | no | authorized validity boundary changes current-use eligibility while application authority applies the transition | durable, attributable, traceable, and use-scoped | [Validity over time](../concepts/validity/validity-over-time.md) |
| presentation | `GeneratedView` | no | Planner may coordinate derivation from eligible state | regenerated when sources or validity change; never scientific authority | [Generated views and session membership](../concepts/research-state/objects-and-state-layers.md#generated-views-and-session-membership) |
| operational recovery and cache | outbox, inbox, lease, fencing, recovery, and cache records | no | application authority owns safe dispatch, replay, retry, and reuse | transactional, append-oriented, or lifecycle-governed by record | [Major non-FCO state families](../concepts/research-state/objects-and-state-layers.md#major-non-fco-state-families) |

For precise definitions and contrasts, use [Terminology](terminology.md).
