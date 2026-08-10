# Protected evaluation

Protected evaluation is the authority-bounded scientific act that applies the
active protocol and decision rule to a closed set of eligible admitted inputs.
It is not open-ended retrieval, a summary pass, governance, or an extra agent.

This page defines the **target design** for EvaluationBundle construction,
evaluation context, and scientific outcomes.

## EvaluationBundle

`EvaluationBundle` is a durable non-FCO closed evaluation input. It may contain
only eligible admitted scientific lineage and provenance for the exact
ScientificInvestigationRun and active protocol revision.

Protected evaluation may use:

- Hypothesis;
- admitted DataProfile reference;
- active protocol revision;
- Evidence obligations;
- AnalysisFrame provenance;
- admitted Evidence;
- method;
- parameters;
- decision rule;
- uncertainty;
- limitations;
- claim scope;
- validity basis.

The bundle must preserve exact references, contract versions, and digests. It
does not copy topical material into the evaluation merely because it appears
relevant.

## Excluded context

EvaluationBundle excludes:

- Assumptions;
- existing Discoveries as inference premises;
- raw conversation;
- generated summaries;
- rejected Tasks;
- failed reasoning;
- unverified GeneratedViews;
- unrelated cross-Objective state.

The exclusion is structural and fail closed. Retrieval scores, prompt
instructions, or a model's judgment cannot override the typed boundary. An
existing Discovery may motivate planning or conflict review, but it cannot be
smuggled into a new protected evaluation as scientific support.

## Evaluation authority

Protected final evaluation belongs to Hypothesis Analyst or the scientific
investigation controller. CogniEDA does not introduce a separate canonical
Evaluator agent.

The scientific authority applies the admitted method, parameters, decision
rule, uncertainty treatment, limitation contract, and claim scope to the
eligible Evidence. Application authority validates the returned typed
transition and applies it; application authority does not reinterpret the
science.

If additional Evidence is required, scientific authority produces another
bounded EvidenceRequest through the admitted path. If the protocol must change
after Evidence exists, the investigation follows the consequential revision
and approval path. Evaluation never silently edits the protocol to fit the
observations.

## Discovery-eligible outcomes

Only these protected-evaluation outcomes may be eligible for a
DiscoveryProposal:

```text
SUPPORTED
CONTRADICTED
VALUABLE_INCONCLUSIVE
```

`VALUABLE_INCONCLUSIVE` is not a generic fallback for weak Evidence. It
requires a completed protocol, a clearly valuable result, a narrowly scoped
claim, a DiscoveryProposal, governance, and authoritative admission.

Eligibility does not guarantee admission. The proposal must still pass
governance and application-authority checks.

## Typed non-Discovery endings

Representative endings that do not create a Discovery include:

```text
NOT_TESTABLE
INSUFFICIENT_DATA
INSUFFICIENT_EVIDENCE
PROTOCOL_EXHAUSTED
OUT_OF_SCOPE
CANCELLED
INVALIDATED
SUPERSEDED
CANCELLED_BY_REPLAN
```

Architectures may distinguish an epistemic outcome from a lifecycle or
termination reason. For example, `INSUFFICIENT_EVIDENCE` describes why the
available admitted observations cannot support an eligible claim, while
`CANCELLED_BY_REPLAN` describes why the investigation stopped. This lifecycle does not
force both categories into a single enum.

A typed ending preserves the completed work, limitations, eligible Evidence,
and termination reason. It does not fabricate a Discovery to satisfy a
cardinality expectation.

## Implementation status

**Design target.** Current bounded Planner answer drafting excludes Assumptions
from its Evidence-only empirical input, but that is not protected scientific
evaluation. The canonical EvaluationBundle, exact contract and digest binding,
protected decision-rule execution, canonical scientific outcomes, and complete
Hypothesis Analyst investigation controller remain **Deferred**. Uncomposed
donor context modules do not establish this capability.
