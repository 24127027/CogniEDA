# Retrieval strategy

Retrieval locates supplemental candidates for a bounded purpose. It does not
confer authority, repair lineage, establish scope, or decide validity. CogniEDA
therefore filters supplemental candidates for structural eligibility before
ranking for relevance.

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

The ordering is normative for supplemental retrieval and purpose-specific use.
A high relevance score cannot rescue a candidate that failed an earlier stage.
It does not apply to the user-governed SessionFrame base: every retained member
must remain available to Planner regardless of lifecycle, score, or result cap.

## Purpose resolution

Retrieval begins with the operation being served: planning, consultation,
scientific investigation control, protected evaluation, Graph Miner inquiry,
answer generation, recovery, or validity review. Without a known purpose and
reasoning mode, the system cannot determine which epistemic types are safe.

Purpose also determines whether the result is supplemental Planner context, an
Evidence-only answer input, an EvaluationBundle input, a read-only inquiry
result, a recovery projection, or a GeneratedView source set. SessionFrame
membership establishes the non-subtractable Planner base, but it is not
interchangeable with any authority-specific input.

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

Before ranking supplemental candidates, retrieval verifies:

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

Ranking chooses among already eligible supplemental candidates. It may consider
recency, exact typed relationships, query overlap, or other explainable signals
appropriate to the purpose. A retained SessionFrame member is not a ranking
candidate: it is already part of Planner's required base context. Membership
still grants visibility rather than scientific authority.

Vector search may support ranking only after eligibility filtering. A vector
score is never an admission check, a validity determination, a cross-Objective
reuse contract, or scientific authority. Implementations must not broaden the
candidate pool after structural filtering by adding semantically similar but
ineligible records.

## Capability grows in stages

Retrieval should become more sophisticated only when authoritative state and
demonstrated need justify it:

```text
deterministic bounded typed context
  -> session-local typed retrieval when required
  -> semantic graph inquiry through Graph Miner
  -> embeddings or hybrid ranking only when evaluation shows value
```

This order keeps memory subordinate to research authority. Embeddings are not
a defining feature of CogniEDA and are not required merely because a session
has history.

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

Planner context contains all resolved SessionFrame members plus any eligible
bounded supplemental candidates, with authoritative references, selection
reasons, limitations, warnings, and exclusions. A separate purpose-specific
input may contain only the eligible records authorized for that use. Bounded
construction reduces accidental category mixing but must never truncate the
SessionFrame-derived Planner base.

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

**Unsupported.** No supplemental retrieval engine or Graph Miner inquiry is
composed into the current bounded runtime. The superseded donor policy,
scoring, retrieval schema, and planning-only Discovery retrieval package have
been removed. The current fresh-context provider exact-materializes every
retained frame member into Planner context, while the Planner graph carries its
active native message history separately and non-authoritatively. Supplemental eligibility-first retrieval
remains **Deferred**.
