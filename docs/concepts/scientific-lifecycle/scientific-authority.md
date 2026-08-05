# Scientific authority

Scientific authority determines whether governed work is testable and, when
it is, authors the scientific commitments needed to investigate it. Planning
may identify that scientific work is needed, but it cannot choose the test that
will determine the answer.

This page defines the **target design** for initiation, feasibility,
operationalization, scientific contracts, and Evidence obligations.

## Scientific initiation

Only an eligible feasible leaf `SCIENTIFIC` Task can enter scientific
investigation and become the source of a Hypothesis.

```text
eligible feasible leaf SCIENTIFIC Task
  -> at most one Hypothesis
```

The application must reject scientific initiation when the Task is a parent,
is merely proposed or unapproved, is not eligible to execute, or is not of
canonical kind `SCIENTIFIC`. A parent Task produces no Hypothesis and no
Discovery. A Task description, user statement, or planning assumption is not
an admitted Hypothesis.

Task meaning is immutable across scientific lineage. If a proposed change
alters its semantic work, the Planner must propose a successor Task rather than
silently editing the existing Task. The canonical Task kinds remain exactly
`DATA`, `SCIENTIFIC`, `GRAPH`, and `SYNTHESIS`; `ANALYTICAL`, `ORGANIZING`, and
`REVIEW` are current legacy vocabulary, not canonical Task kinds.

## Feasibility belongs to Hypothesis Analyst

Hypothesis Analyst owns the scientific feasibility decision. Its result must
distinguish at least these meanings:

- feasible;
- not testable;
- insufficient data;
- out of scope;
- blocked by unavailable capability;
- requires approval or additional grounding.

Only a feasible result for an otherwise eligible leaf Task permits a canonical
Hypothesis candidate. Hypothesis Analyst may propose that candidate;
application authority validates its identity, lineage, cardinality, and typed
contracts before admission. Planner does not author the scientific Hypothesis,
and application authority does not invent its content.

## ScientificInvestigationRun

`ScientificInvestigationRun` is a durable non-FCO lifecycle record for one
governed scientific investigation. Conceptually, it binds:

- Objective and PlanRevision scope;
- the source Task and its feasibility state;
- the Hypothesis when admitted;
- the InvestigationPlan and active protocol revision;
- Evidence obligations and EvidenceRequest rounds;
- admitted Evidence and the EvaluationBundle;
- the scientific outcome;
- a DiscoveryProposal when one exists;
- governance and admission references;
- the termination reason when investigation stops.

These are conceptual obligations, not a frozen database or wire schema. The
record preserves continuity across repeated requests, retries, protocol
revisions, governance loops, and safe non-completion without becoming an FCO
or semantic Knowledge Graph node.

## InvestigationPlan and InvestigationProtocol

`InvestigationPlan` and `InvestigationProtocol` are durable non-FCO scientific
records. Hypothesis Analyst owns their scientific content. Depending on the
investigation, that content may define:

- population or cohort;
- variables;
- measurement semantics and units;
- method and parameters;
- decision rule;
- uncertainty treatment;
- limitation contract;
- claim scope;
- stopping conditions;
- Evidence obligations;
- reproducibility requirements.

Planner must not define or revise these scientific fields. Application
authority validates and admits the exact candidate under the applicable
approval and lineage rules.

A protocol change after Evidence exists is consequential. It requires the
appropriate approval and scientific-authority path, a traceable protocol
revision, and reevaluation of which Evidence remains eligible. Silent in-place
protocol mutation is prohibited.

## Eight canonical scientific contract categories

For the current frozen architecture, C2 conceptually owns eight canonical
scientific contract schemas:

1. population or cohort;
2. variables;
3. measurement semantics and units;
4. DataProfile identity;
5. method and protocol;
6. uncertainty;
7. limitations;
8. claim scope.

Hypothesis Analyst may propose typed candidates. Application authority
validates and admits immutable canonical records. Unit C defines their semantic
roles and authority boundaries; it does not invent exact field layouts that
have not been frozen.

Canonicalization is structural only:

- deterministic typed validation;
- canonical ordering;
- duplicate rejection;
- fixed serialization;
- schema-version binding;
- digest computation.

It performs no semantic normalization: no synonym resolution, inferred unit
conversion, fuzzy variable mapping, population inference, method-compatibility
inference, limitation interpretation, claim-scope implication, or model,
ontology, or compatibility-registry call. An input that cannot be expressed in
the finite typed schemas is rejected. It is not guessed into canonical form.

## Evidence obligations and EvidenceRequest

Hypothesis Analyst owns the Evidence obligations required by the active
protocol. It may issue multiple EvidenceRequests as the investigation
progresses.

An `EvidenceRequest` is a bounded typed request that identifies a specific
observation obligation and binds to the scientific investigation and active
protocol revision. It is neither Evidence nor a generic prompt, and it grants
no scientific-evaluation authority to Data Explorer.

Application authority admits the exact request and coordinates execution. Data
Explorer receives a `DataWorkOrder` derived from that admitted request. The
derivation may project execution details, but it must preserve request,
protocol, obligation, scope, and lineage identity without adding scientific
meaning.

## Authority split

| Act | Planner | Hypothesis Analyst | Application authority |
| --- | ---: | ---: | ---: |
| identify and route scientific work | owns | consulted or invoked | validates route and eligibility |
| decide feasibility | no | owns | validates and records transition |
| author Hypothesis candidate | no | owns | admits or rejects exact candidate |
| author InvestigationPlan, protocol, and obligations | no | owns | admits or rejects exact records |
| access datasets | no | no | coordinates Data Explorer boundary |
| perform protected final evaluation | no | owns | validates and applies transition |

No agent receives durable admission authority from authorship. See
[Evidence and AnalysisFrames](evidence-and-analysis-frames.md) for the
observation and provenance boundary.

## Implementation status

**Design target with partial legacy support.** Current source enforces a
repository-level one-Hypothesis-per-leaf guard using the legacy `ANALYTICAL`
Task kind and stores scientific fields directly on current Task/Hypothesis
models. Canonical feasibility outcomes, `ScientificInvestigationRun`,
InvestigationPlan, InvestigationProtocol, Evidence obligations, EvidenceRequest,
and the eight immutable canonical contract schemas are not implemented. The
placeholder Hypothesis Analyst graph is not runnable and currently declares a
dataset tool, which is a known deviation from the canonical no-dataset-access
boundary.
