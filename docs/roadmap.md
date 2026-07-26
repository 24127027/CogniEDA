# CogniEDA capability roadmap

> **Implementation status:** **Partially implemented**.
>
> This is a capability roadmap, not a release history or proof of current
> behavior. Source code remains authoritative for implementation status.

CogniEDA has a guarded in-process scientific spine, but it does not yet have a
supported end-user product surface. The roadmap therefore advances by
capability and preserved invariant rather than by repository package or
implementation chronology.

## Protected foundation

The following boundaries are **Implemented** and **Verified on SQLite**:

- the eight-object research-state ontology and core lifecycle guards;
- approved terminal analytical Task to Hypothesis cardinality;
- observation-only executor output and atomic Evidence admission;
- protected Hypothesis evaluation that returns a proposal or typed failure;
- principal-bound governance over an exact persisted proposal;
- atomic Discovery-chain admission;
- atomic validity propagation with historical retention and active exclusion;
- bounded SessionFrame projections and validity-first Discovery retrieval.

These statements concern the checked-in in-process path. They do not imply that
a production CLI, API, worker, model provider, authentication provider, or Data
Explorer adapter exists.

## Next product slice

The next coherent product slice is a **Design target**:

1. provide an authenticated user entry point;
2. wire a production model adapter and a concrete observation-only Data
   Explorer;
3. expose Task and execution proposal approval without bypassing durable
   authority;
4. run the existing Evidence, evaluation, governance, Discovery, and validity
   services through a supported worker/application boundary;
5. surface active SessionFrame context and validity state to the user;
6. preserve idempotency, exact-proposal authorization, and atomic scientific
   writers end to end.

The slice is not complete until the user can distinguish proposed work,
approved execution, observed Evidence, proposed interpretation, authorized
Discovery, and invalidated history.

## Capability work after the first product slice

The following areas are **Partially implemented** or **Deferred**:

- governed dataset versioning, cleaning, and executable DVC integration;
- complete Planner answer, suggestion, review, conflict, pause, and resume
  branches;
- user-governed SessionFrame item management and robust project resume;
- Graph Miner traversal and a persistent semantic or vector index;
- validity-keyed Evidence caching that cannot author scientific claims;
- broader reproducibility capture for code, environment, seeds, and artifacts;
- service/worker deployment, multi-user policy, observability, and recovery;
- database portability beyond the SQLite boundary;
- tracked CI policy and strict static-typing remediation.

## Invariants that roadmap work must preserve

Future capability work must not:

- promote non-FCO workflow, provenance, cache, or generated-view records into
  durable scientific knowledge;
- allow proposed or non-terminal Tasks to execute;
- allow Assumptions into protected Discovery synthesis;
- let a specialist authorize or persist its own proposal;
- let a parent Task manufacture a Discovery from several child claims;
- mutate the scientific core of DataProfile or Evidence;
- make invalid or deprecated knowledge active merely because it is relevant;
- create an alternate writer for Evidence, Discovery, or validity effects.

For a source-oriented list of current gaps, see
[Implementation gap analysis](architecture/implementation-gap-analysis.md).
The prerequisite boundary for the next product slice is
[Product surface and bootstrap boundary](product-surface-and-bootstrap-boundary.md);
Planner extraction triggers are in
[Planner boundary and operation model](planner-boundary-and-operation-model.md).
For the conceptual reading path, return to the
[documentation index](index.md).
