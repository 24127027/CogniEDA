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
| `Hypothesis` | FCO; scientific commitment | yes | Hypothesis Analyst owns feasibility and operationalization; application authority admits | At most one for an eligible feasible leaf `SCIENTIFIC` Task | lifecycle-governed | [Planning and scientific state](../concepts/research-state/planning-and-scientific-state.md#eligibility-for-scientific-investigation) |
| `Evidence` | FCO; observation-backed scientific record | yes | application authority owns admission | Binds admitted observation to Hypothesis, DataProfile, AnalysisFrame, ExecutionRun, method, and provenance | immutable; replacement uses new Evidence and lifecycle relation | [Planning and scientific state](../concepts/research-state/planning-and-scientific-state.md#observation-evidence-and-provenance) |
| `Discovery` | FCO; evidence-bound claim | yes | scientific authority authors proposal; governance authorizes; application authority admits | Scoped claim with validity basis; at most one per Hypothesis | admitted claim content remains fixed; lifecycle and validity governed | [Planning and scientific state](../concepts/research-state/planning-and-scientific-state.md#discovery-is-conditional-not-automatic) |
| `SessionFrame` | FCO; active context | no | Planner coordinates selection; application authority persists | Governed bounded context for a purpose, scope, and Objective | lifecycle-governed context projection | [Research-state foundation](../concepts/research-state/index.md#continuity-without-category-collapse) |

## Major non-FCO families

The examples are representative, not exhaustive. A non-FCO record may still be
durable, immutable, transactionally important, or authoritative within its own
boundary.

| Family | Representative records | In semantic graph? | Conceptual authority and purpose | State posture | Full explanation |
| --- | --- | ---: | --- | --- | --- |
| planning and plan versioning | `PlanRevision`, `PlanTaskBinding`, `PlanTaskDependency`, `TaskLifecycleRecord`, `TaskPresentationMetadata`, `PlannerConsultationRun` | no | Planner proposes and coordinates; application authority admits plan membership, dependency, assignment, ordering, and approval state | versioned or lifecycle-governed | [Task and PlanRevision](../concepts/research-state/planning-and-scientific-state.md#task-is-work-planrevision-is-a-plan) |
| scientific investigation | `ScientificInvestigationRun`, feasibility record, `InvestigationPlan`, `InvestigationProtocol`, `ProtocolRevision`, `EvidenceRequest` | no | Hypothesis Analyst or investigation controller owns feasibility, operationalization, protocol, and Evidence obligations; application authority owns durable transitions | append-oriented, versioned, or lifecycle-governed by record | [Eligibility](../concepts/research-state/planning-and-scientific-state.md#eligibility-for-scientific-investigation) |
| execution and provenance | `ExecutionRun`, `AnalysisFrame` | no | Data Explorer returns bounded work; application authority records attempt and exact data view | append-oriented provenance; attempt lifecycle governed | [Observation and provenance](../concepts/research-state/planning-and-scientific-state.md#observation-evidence-and-provenance) |
| evaluation and outcome | `EvaluationBundle`, `ScientificInvestigationOutcome`, `DiscoveryProposal` | no | protected scientific evaluation owns interpretation and typed outcome or proposal | content-bound records; lifecycle governed where applicable | [Protected evaluation](../concepts/research-state/planning-and-scientific-state.md#protected-evaluation-and-outcomes) |
| governance and admission | `GovernanceDecision`, admission records | no | governance authorizes exact eligible proposals; application authority validates and applies transitions | append-oriented authority record | [Protected evaluation](../concepts/research-state/planning-and-scientific-state.md#protected-evaluation-and-outcomes) |
| validity | validity events and review signals | no | authorized validity boundary changes current-use eligibility while preserving history | append-oriented and lifecycle-governed | [Historical truth and current authority](../concepts/research-state/identity-scope-and-lineage.md#historical-truth-and-current-authority) |
| presentation | `GeneratedView` | no | Planner may coordinate derivation from eligible state | regenerated when sources or validity change; never scientific authority | [Generated views and active context](../concepts/research-state/objects-and-state-layers.md#generated-views-and-active-context) |
| operational recovery and cache | outbox, inbox, lease, fencing, recovery, and cache records | no | application authority owns safe dispatch, replay, retry, and reuse | transactional, append-oriented, or lifecycle-governed by record | [Major non-FCO state families](../concepts/research-state/objects-and-state-layers.md#major-non-fco-state-families) |

For precise definitions and contrasts, use [Terminology](terminology.md).
