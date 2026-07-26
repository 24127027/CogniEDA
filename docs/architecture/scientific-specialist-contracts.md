# Scientific Specialist Contracts

> **Role:** Technical reference. **Canonical concept owner:**
> [Scientific authority](../concepts/scientific-lifecycle/scientific-authority.md).
> **Contributor entry:** [Contributor documentation](../development/index.md).
> **Current-state owner:** [CogniEDA current state](../current-state.md).

> **Implementation status:** protected specialist boundaries **Implemented**;
> concrete production adapters **Unsupported**.

The canonical rationale is [Scientific authority](../concepts/scientific-lifecycle/scientific-authority.md);
the closed-input explanation is
[Protected evaluation](../concepts/scientific-lifecycle/protected-evaluation.md). This page
retains the compact contract matrix for implementers.

## Authority matrix

| Component | Observe | Evaluate Evidence | Author proposal wording | Decide | Persist |
| --- | ---: | ---: | ---: | ---: | ---: |
| Data Explorer adapter | yes | no | no | no | no |
| Hypothesis Analyst | no | yes | yes | no | no |
| Governance services | no | no | no | record exact authority/decision | authority and decision records only |
| Discovery admission | no | no | no | verify approved decision | exact authorized Discovery chain |
| Planner | no | no | no | stage approved workflow operations | no Evidence/Discovery writer |

## Data Explorer

`DataExplorerDispatcher` invokes one explicitly registered
`DataExplorerAdapterProtocol`. The adapter receives a `DataExplorerInput` containing durable
Task, Hypothesis, DataProfile, and ExecutionRun identities plus the admitted contract. It returns
`DataExplorerSuccessResult` or `DataExplorerFailureResult`.

Success output contains `AnalysisFrameObservation` and `EvidenceObservation`. It contains no
scientific evaluation or Discovery wording. The adapter has no repository, SQL session, governance,
or transaction authority. No concrete production adapter is checked in.

## Hypothesis Analyst

`application.evaluation.bundle_builder.build_synthesis_bundle` reconstructs a closed,
repository-authoritative `DiscoverySynthesisBundle`. The bundle contains only:

- Hypothesis contract;
- safe accepted DataProfile metadata;
- AnalysisFrame and ExecutionRun provenance;
- active admitted Evidence;
- method parameters, decision rule, limitations, invalidators, and digests.

The no-tool PydanticAI agent receives that bundle as its only dependency, with no message history.
The schema has no generic context field, so Assumptions, prior Discoveries, SessionFrames, chat,
retrieval scores, raw data, and files cannot be injected through the supported runner.
Hypothesis Analyst returns a typed `DiscoveryProposal` or `EvaluationFailure`.

## Evaluation, governance, and admission

`EvaluationTransitionService` owns evaluation-control enqueue/claim/retry/proposal publication.
`GovernanceAuthorityIssuer` independently issues expiring principal-bound authority.
`DiscoveryAdmissionGovernanceService` records and verifies the exact decision; it does not author
or materialize the claim.

`AtomicDiscoveryAdmissionService` rebuilds the current bundle and proposal authority under the
SQLite writer lock. It copies the authorized proposal exactly into `Discovery`, creates the
conclusion SessionFrame, transitions Hypothesis/Task/evaluation/claim state, and consumes the
decision in one commit.

## Explicitly rejected claims

- Data Explorer does not evaluate.
- The application layer does not rewrite Discovery wording.
- Governance and Planner do not create Discovery.
- Assumptions do not enter protected conclusion synthesis.
- Repositories do not own these multi-record transactions.
