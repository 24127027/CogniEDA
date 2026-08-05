# Retrieval strategy

Retrieval locates candidates for a bounded purpose. It does not confer
authority, repair lineage, establish scope, or decide validity. CogniEDA
therefore filters for structural eligibility before ranking for relevance.

This page defines the **target design** for eligibility-first retrieval,
Graph Miner, ranking, and fail-closed construction.

## Canonical ordering

```text
purpose resolution
  -> Objective and scope binding
  -> type eligibility
  -> authority and lifecycle checks
  -> validity checks
  -> lineage and contract checks
  -> permitted-use filtering
  -> relevance ranking
  -> bounded context construction
```

The ordering is normative. A high relevance score cannot rescue a candidate
that failed an earlier stage.

## Purpose resolution

Retrieval begins with the operation being served: planning, consultation,
scientific investigation control, protected evaluation, Graph Miner inquiry,
answer generation, recovery, or validity review. Without a known purpose and
reasoning mode, the system cannot determine which epistemic types are safe.

Purpose also determines whether the result is a SessionFrame selection, an
EvaluationBundle input, a read-only inquiry result, a recovery projection, or
a GeneratedView source set. These are not interchangeable outputs.

## Objective and scope binding

The request is bound to an exact Objective and applicable DataProfile,
population, cohort, protocol, claim, and permitted-use scope before candidate
selection. A Workspace may contain many active Objectives; Workspace
membership alone is not sufficient scope.

SessionFrame remains Objective-scoped unless a specific authorized operation
explicitly permits otherwise. Related prior work may suggest a new Objective,
but it does not become state in the current Objective.

Cross-Objective Evidence reuse requires explicit admission and exact equality
over the relevant versioned canonical typed obligations. Fuzzy similarity,
natural-language equivalence, nearest-neighbor proximity, and model judgment
cannot establish that equality.

## Eligibility filters

Before ranking, retrieval verifies:

- the candidate's recognized type and authority class;
- lifecycle eligibility for the requested mode;
- current validity and freshness;
- exact Objective and DataProfile scope;
- required scientific lineage, contracts, references, and digests;
- whether the requested use is permitted;
- explicit exclusions for the mode.

Unknown types, missing lifecycle, unresolved Objective, incomplete lineage,
ambiguous contract version, or uncertain validity fail closed. The result
records exclusions or blockers rather than returning unsafe context.

## Ranking after eligibility

Ranking chooses among already eligible candidates. It may consider recency,
explicit SessionFrame selection, exact typed relationships, query overlap, or
other explainable signals appropriate to the purpose.

Vector search may support ranking only after eligibility filtering. A vector
score is never an admission check, a validity determination, a cross-Objective
reuse contract, or scientific authority. Implementations must not broaden the
candidate pool after structural filtering by adding semantically similar but
ineligible records.

## Graph Miner

Graph Miner is a read-only inquiry specialist. It may help locate:

- typed relations and valid paths;
- lineage dependencies;
- gaps and missing obligations;
- conflicts and contradiction candidates;
- validity events and review state;
- related Objective suggestions;
- bounded neighborhoods for an authorized inquiry.

Graph Miner cannot mutate state, decide eligibility by itself, perform dataset
operations, create Evidence or Discovery, or admit cross-Objective relations.
Its result returns references, limitations, and blockers to the requesting
mode; application authority still enforces selection and admission.

## Bounded context construction

The final context contains only the eligible subset needed for the operation,
with authoritative references, selection reasons, limitations, warnings,
exclusions, and size bounds. Bounded construction reduces accidental category
mixing and makes the selection auditable.

Retrieval results and summaries remain projections. Protected evaluation
requires a closed EvaluationBundle validated against its exact scientific
lineage, not a generic search result.

## Fail-closed examples

| Condition | Required response |
| --- | --- |
| Objective identity is missing | do not retrieve Workspace-wide state as current authority |
| Evidence is active but protocol binding is unresolved | exclude it from protected evaluation |
| a Discovery is semantically similar but belongs to another Objective | do not import it; at most suggest related prior work through an authorized planning path |
| an unverified GeneratedView ranks highly | exclude it as scientific support |
| a validity event cannot be resolved | block the affected current use and request review |
| Graph Miner finds a possible cross-Objective path | return it only as a bounded suggestion; do not admit the relation |

## Implementation status

**Partially implemented with an important scope limitation.** Current source
has a pure policy that filters known object and lifecycle combinations by four
legacy modes. A bounded planning-only `DiscoveryRetrievalEngine` filters
Discovery lifecycle before deterministic lexical ranking and can prioritize
references already present in a SessionFrame. No vector retrieval is used.

The current retrieval request and SessionFrame do not bind an Objective
identifier, and the engine can enumerate Workspace-local Discoveries before
ranking. It therefore does not establish canonical Objective isolation or
cross-Objective admission and must not be described as the complete target
retrieval boundary. Full authority, validity-event, scientific-contract, and
lineage filtering remain incomplete.
