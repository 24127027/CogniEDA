# Evidence and AnalysisFrames

CogniEDA separates a request for observation, an execution attempt, the exact
data view, a returned observation candidate, and admitted Evidence. Each has a
different authority and lifecycle.

This page defines the **target design** for scientific data execution,
provenance, and Evidence admission.

## Canonical observation sequence

```text
admitted EvidenceRequest
  -> DataWorkOrder
  -> Data Explorer
  -> DataExplorerResult
  -> ExecutionRun
  -> AnalysisFrame
  -> EvidenceObservation candidate
  -> Evidence admission
```

An `EvidenceRequest` is an admitted bounded scientific request. Application
coordination derives the role-native `DataWorkOrder`. Data Explorer executes
only that order and returns a `DataExplorerResult`. Application authority then
validates the attempt, exact analytical view, candidate observation, and
scientific lineage before any Evidence exists.

Data Explorer exclusively accesses datasets. This exclusivity does not grant
it authority to define a Hypothesis, change the protocol, interpret the final
scientific outcome, govern a proposal, or admit Evidence.

## EvidenceRequest and DataWorkOrder

An EvidenceRequest:

- is not Evidence;
- is not a generic prompt;
- is a bounded typed request;
- binds to its ScientificInvestigationRun and active protocol revision;
- identifies the Evidence obligation to be observed;
- does not grant Data Explorer scientific-evaluation authority.

Application authority admits the request and coordinates execution. The
derived DataWorkOrder contains only the role-native data operation, eligible
dataset reference, constraints, required outputs, resource limits, and
stopping conditions necessary to satisfy that exact request. Derivation must
not broaden scope or invent new scientific semantics.

## ExecutionRun

`ExecutionRun` is a durable non-FCO provenance record for one execution
attempt. A retry is a new traceable attempt rather than an edit to the prior
record. Attempt identity, admitted work identity, lease and fencing posture,
result digest, code and environment identity, and predecessor/retry lineage
are preserved as required by the execution contract.

An ExecutionRun is not the ScientificInvestigationRun. One scientific
investigation may require multiple EvidenceRequest rounds and multiple
execution attempts.

## AnalysisFrame

`AnalysisFrame` is durable non-FCO provenance identifying the exact analytical
view used by one bounded operation. It fixes which admitted DataProfile and
which relevant columns, filters, cohorts, transformations, or view identity
were actually used.

An AnalysisFrame is not:

- a DataProfile;
- a raw dataset;
- Evidence;
- a generated table;
- a semantic Knowledge Graph node;
- an FCO.

The view may be referenced by an artifact, digest, or other stable identity,
but this conceptual contract does not prescribe a database table or storage
layout.

## EvidenceObservation candidate

`DataExplorerResult` may contain an `EvidenceObservation` candidate: the
bounded observed output, diagnostics, uncertainty material, limitations, and
artifact references returned for the obligation. The candidate is not
Evidence. Data Explorer cannot promote it by calling it evidence, and a
successful tool exit does not imply admission.

## Evidence traceability

Evidence must remain traceable to:

- Hypothesis;
- admitted DataProfile;
- InvestigationProtocol or exact revision;
- Evidence obligation;
- EvidenceRequest;
- ExecutionRun;
- AnalysisFrame;
- method and parameters;
- limitations and uncertainty;
- relevant artifact and environment digests.

These references establish scientific and provenance identity. They are not a
list of concrete schema fields, tables, or storage joins.

## Evidence admission

Evidence admission performs no semantic canonicalization. Application
authority must exact-copy canonical references and digests from the admitted
scientific lineage into the Evidence candidate and reject the transition when
it encounters:

- a missing required reference;
- a reference or digest mismatch;
- an invalid DataProfile binding;
- a protocol or protocol-revision mismatch;
- an observation outside the Evidence obligation;
- non-authoritative execution lineage.

Admission may validate finite typed structure, identity, equality, cardinality,
digests, lifecycle eligibility, and provenance. It may not resolve synonyms,
infer units, map variables fuzzily, infer populations, judge method
compatibility, interpret limitations, imply claim scope, or call a model,
ontology, or compatibility registry to repair meaning.

Evidence is immutable admitted scientific content. Correction requires new
Evidence plus an explicit lifecycle or validity relation to the prior record.
Neither an agent nor application authority edits admitted Evidence in place.

## Implementation status

**Design target.** Current source provides partial provenance support through
minimal `ExecutionRun` and `AnalysisFrame` schemas and repositories, immutable
Evidence models, optional strict dereferencing of AnalysisFrame and
ExecutionRun references, and some profile/Hypothesis consistency checks. It
does not implement admitted EvidenceRequest lineage, role-native DataWorkOrder
and DataExplorerResult contracts, EvidenceObservation candidates, canonical
reference/digest exact-copy admission, or the complete fail-closed admission
contract described here.
