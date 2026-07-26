# Scientific authority

CogniEDA separates observation, scientific interpretation, authorization, and
durable materialization because each action grants a different kind of
authority. The purpose is epistemic, not merely organizational:

> Prevent the wrong component from manufacturing, modifying, or legitimizing a
> scientific claim.

The governing thesis remains:

> CogniEDA is validity-preserving research-state infrastructure.

Conclusion validity and traceability come first, context type safety comes
second, and multi-session continuity comes third. A convenient workflow is not
allowed to reverse that order.

> **Implementation status:** The guarded in-process authority chain is
> **Implemented** and its transaction, replay, fencing, and concurrency behavior
> is **Verified on SQLite**. A concrete production Data Explorer, production
> authentication provider, default production Analyst model adapter, and
> production CLI, API, worker, daemon, or deployment bootstrap are
> **Unsupported**.

## The authority chain

The supported scientific handoff is:

```text
Data Explorer observes
  -> Evidence is admitted
  -> Hypothesis Analyst proposes
  -> governance authorizes
  -> application materializes exactly
```

No arrow means that the next component may inherit all authority of the previous
one. Each boundary narrows what can be accepted and what can be written.

| Boundary | Authority it holds | Authority it does not hold |
| --- | --- | --- |
| Data Explorer | produce typed observations and technical diagnostics | evaluate a Hypothesis, choose a scientific outcome, persist research state |
| Evidence admission | validate and materialize observation and provenance | interpret Evidence, complete the Task, create a Discovery |
| Hypothesis Analyst | evaluate one protected bundle and author one proposal or typed failure | retrieve generic context, govern, persist, or mutate lifecycle state |
| application evaluation | reconstruct protected input and persist the exact typed Analyst result | invent or improve scientific meaning |
| governance | issue and verify authority; approve, reject, or cancel an exact proposal | edit a proposal or create a Discovery |
| Discovery admission | revalidate authority and atomically copy the authorized proposal | paraphrase, narrow, broaden, or otherwise reinterpret it |

This division prevents authority laundering: an observation cannot become a
claim merely because it crossed an application boundary, and an approval cannot
be treated as scientific authorship merely because it permits a write.

## Why one component must not both compute and interpret

In the running example, the approved analysis asks whether longer
first-response time is associated with 90-day churn in the 2025 small-business
subscription cohort. A Data Explorer may fit the approved method and observe an
effect estimate, uncertainty, threshold result, and limitations.

The tempting simpler design is to let that executor return a polished
conclusion. It already has the numbers, so combining computation and
interpretation appears efficient. That alternative is unsafe here:

- execution-specific assumptions can leak into the wording;
- a technical success can be confused with scientific support;
- fail-to-reject can be strengthened into a claim of no relationship;
- the executor can omit limitations that make its result less persuasive;
- retries can produce competing interpretations of the same durable attempt;
- the component under evaluation becomes the judge of what its output means.

CogniEDA therefore gives the Data Explorer observation authority only. Its
success contract contains an `AnalysisFrameObservation`,
`EvidenceObservation`, execution details, and bounded diagnostics. Its failure
contract contains a typed technical failure. Neither contract contains an
epistemic outcome or `DiscoveryProposal`.

This boundary protects the distinction between observed result and
interpretation. The cost is a separate evaluation lifecycle and more explicit
contracts. It should be revisited only if a replacement design can preserve
independent scientific proposal authority rather than hiding interpretation
inside executor output.

The executor contract is **Implemented**. A concrete production Data Explorer
is **Unsupported**. Test adapters demonstrate the boundary; they are not a
product capability.

## Evidence admission stops before interpretation

A successful executor response is still only an unadmitted observation.
Evidence admission reconstructs the durable attempt authority, validates the
approved Task, Hypothesis, DataProfile, method, parameters, inbox, outbox,
digests, lease, and fence, then commits:

- the `AnalysisFrame` provenance;
- immutable `Evidence`;
- the `ExecutionRun` transition to `EVIDENCE_ADMITTED`;
- the Hypothesis transition to `READY_FOR_EVALUATION`;
- consumption of the authoritative result inbox.

The direct analytical Task remains `ACTIVE`, and no Discovery is created.

It would be simpler to interpret and finalize the result in the same
transaction. That would let observation admission decide scientific meaning
before a protected evaluator had seen the complete authoritative lineage. It
would also make executor retry and scientific finalization share one authority
boundary.

Separating the transactions protects two independent questions:

1. Did this approved execution produce an admissible observation?
2. What bounded scientific claim, if any, does that admitted Evidence justify?

The tradeoff is an intermediate `READY_FOR_EVALUATION` state and a second
recoverable workflow. The boundary should be reconsidered only if observation
admission and independent evaluation can remain separately auditable and
failure-safe.

Evidence admission is **Implemented** and **Verified on SQLite**. It is not a
Discovery admission path.

## The Hypothesis Analyst is the sole scientific proposal author

The Hypothesis Analyst receives one closed
`DiscoverySynthesisBundle` and returns exactly one typed result:

```text
DiscoverySynthesisBundle
  -> DiscoveryProposal | EvaluationFailure
```

The Analyst alone chooses the proposal's scientific wording and one of the
bounded epistemic outcomes: supported, contradicted, inconclusive, or
insufficient evidence. The input contract, its exclusions, and its repository
construction are explained in
[Protected evaluation](protected-evaluation.md).

The tempting alternative is to let an application service assemble a prompt,
call a model, and then clean up the response. That makes apparently harmless
application behavior—adding default prose, sorting content, normalizing scope,
or removing repetition—part of scientific authorship. Authority becomes
ambiguous because neither the Analyst output nor the stored claim is the sole
source of meaning.

CogniEDA instead isolates the Analyst:

- its only dependency is the typed bundle;
- it has no tools;
- it receives no message history;
- it cannot access repositories, SQL sessions, files, governance, or
  application services;
- its output is validated against the exact bundle before publication.

This protects scientific proposal authority and context type safety. The cost
is that proposal quality must be adequate at the Analyst boundary; application
code is not allowed to rescue weak scientific prose by rewriting it. A default
production model adapter remains **Unsupported** and must be supplied by
deployment composition.

## Application services construct and persist; they do not interpret

Application services are trusted to perform deterministic coordination:

- reconstruct the protected bundle from authoritative repositories;
- validate lifecycle, lineage, scope, method, parameters, and active Evidence;
- bind proposal, bundle, Evidence set, principal, decision, and contract
  identities;
- own claim, lease, fencing, compare-and-set, replay, and transaction behavior;
- persist the exact typed Analyst output or typed evaluation failure.

They must not:

- invent a claim;
- paraphrase proposal wording;
- broaden or narrow scope;
- change epistemic status;
- replace uncertainty;
- remove limitations or invalidators;
- replace an `EvaluationFailure` with guessed scientific text.

This is deliberately a narrower role than “business logic may normalize
everything before storage.” The invariant is that a reader can identify one
scientific author: the Analyst that produced the persisted proposal. The
tradeoff is stricter compatibility and less opportunity for automatic
application-layer polish.

Presentation changes belong in a `GeneratedView`, not in mutation of the
proposal or Discovery. `GeneratedView` remains a **Design target** rather than a
current complete product workflow.

## Governance authorizes without becoming a scientific author

Governance resolves or accepts independently issued authority, verifies the
principal and its workspace/session/purpose/operation scope, reconstructs the
current proposal lineage, and records one decision:

```text
APPROVED
REJECTED
CANCELLED
```

There is no hidden `MODIFY` outcome. Approval means that the exact proposal
bound to the decision may proceed to admission. Rejection and cancellation mean
that no Discovery may be materialized from that decision.

The tempting alternative is an approval screen that lets a user edit the claim
and approve the edited text in one step. That turns governance into an
unvalidated scientific author and breaks the link to the protected bundle. A
scientific change requires a new valid proposal and a corresponding new
decision, not an in-place edit.

Governance protects accountable authorization while keeping scientific
authorship separate. Its cost is another durable record and another review
cycle for changed wording. Production authentication and a complete
user-facing approval workflow are **Unsupported** or **Partially implemented**;
the in-process authority and decision services are **Implemented**.

## Exact proposal-copy

The durable Discovery copies every scientific field from the authorized
persisted `DiscoveryProposal` exactly:

- claim statement, scope, conditions, and observed-result interpretation;
- epistemic status;
- Evidence identities;
- scope;
- complete validity basis, including DataProfile, AnalysisFrame references,
  Hypothesis, method, parameters, code/environment references, decision rule,
  strength, uncertainty, Assumption exclusion, and invalidators;
- limitations.

The application adds only deterministic durable identity, creation time,
lifecycle metadata, and transaction bindings. The existing
`analysis_intent` field is copied unchanged from the already bound source
Hypothesis as lineage metadata; it is not derived by the application. The
Discovery's convenience fields for uncertainty and invalidators are copied from
the same proposal validity basis.

No paraphrasing, truncation, semantic sorting, set conversion, scope rewriting,
uncertainty rewriting, or limitation removal is allowed. Canonical ordering may
be required before the Analyst proposal is accepted, but admission does not
reorder scientific content.

This rule makes scientific authority unambiguous and prevents application code
from silently “improving” a claim into a different claim. The tradeoff is that a
poorly written but valid proposal must be rejected and regenerated rather than
edited during admission. Focused tests compare the persisted Discovery with the
proposal across every scientific field.

Atomicity, replay, and changed-binding behavior for this copy are explained in
[Discovery governance and admission](discovery-governance-and-admission.md).

## Stopping paths and epistemic outcomes

The authority chain is allowed to stop. Cardinality is “at most one” because
safe failure must not manufacture knowledge merely to complete a workflow.

### Supported

Evidence supports the bounded Hypothesis claim under the approved scope,
method, decision rule, and uncertainty. It does not establish a broader or
causal claim unless that exact contract warrants one.

### Contradicted

Evidence conflicts with the Hypothesis as stated within the evaluated scope. A
contradicted result does not automatically support the inverse claim. The
proposal may make that stronger statement only when the Evidence and contract
explicitly justify it.

### Inconclusive

The admitted Evidence does not permit a stable directional conclusion under the
evaluation contract. Inconclusive is a scientific outcome, not an evaluation
transport failure.

### Insufficient evidence

The Evidence does not satisfy the threshold required for the claim. In the
running example, the safe form is:

> Available Evidence is insufficient to establish an association within the
> stated cohort using the approved method and decision rule.

It is not proof that no relationship exists.

### EvaluationFailure

The protected Analyst cannot produce a valid proposal because input, lineage,
identifiability, provider behavior, contract support, or structured output is
inadequate. The application persists the typed failure; it does not invent a
conclusion. No Discovery is created.

### Governance rejection or cancellation

The proposal and decision remain governance history, but they are not active
scientific knowledge. No Discovery is created, and rejection does not become a
scientific result.

### Technical execution failure

Execution provenance and technical diagnostics may remain durable. Without a
valid observation there is no admitted Evidence, and without Evidence there is
no evidence-bound Discovery.

## Common authority-laundering failures

These designs are forbidden even when their output sounds scientifically
reasonable:

- treating an executor result summary as a Discovery;
- feeding SessionFrame summaries, chat, Assumptions, or prior Discoveries to
  the protected Analyst;
- asking governance to repair proposal wording;
- adding “helpful” application defaults to scope, uncertainty, or limitations;
- persisting an approval-time edit that was never evaluated;
- using a generated answer or cached summary as a scientific premise;
- admitting only the Discovery insert while leaving its lifecycle chain
  incomplete;
- calling a test adapter evidence that a production specialist exists.

Each failure gives a component authority that its input did not justify.

## Design costs and revisit triggers

| Decision | Cost introduced | Revisit when |
| --- | --- | --- |
| observation-only Data Explorer | a separate evaluation step | an alternative preserves independent interpretation authority |
| separate Evidence and Discovery admission | intermediate states and recovery logic | both boundaries can remain separately auditable under a new workflow |
| sole Analyst proposal authorship | proposal regeneration instead of application edits | a formally equivalent authoring boundary is demonstrated |
| tool-free closed Analyst input | lower convenience and no ad hoc lookup | a new typed input category is shown to be authoritative and safe |
| governance without editing | another proposal cycle for wording changes | edited content can be independently reevaluated and rebound |
| exact proposal-copy | no storage-time prose cleanup | presentation needs are handled by GeneratedViews |
| SQLite-bounded atomic admission | single-database deployment constraint | another backend has equivalent focused transaction and race verification |

These are local optima, not timeless implementation forms. Their protected
invariants—traceable scientific authorship, context type safety, exact
authorization, and all-or-nothing admission—must survive any redesign.

## Related decision rationale

[Design decisions and tradeoffs](../../design-decisions/index.md) classifies
which authority boundaries must survive a redesign.
[Scientific authority by role](../../design-decisions/scientific-authority-by-role.md) preserves the
specialist-authority decision, and
[Creating Discoveries after authorization](../../design-decisions/creating-discoveries-after-authorization.md) preserves the
all-or-nothing admission decision.

## Implementation orientation

The main source boundaries are:

- `src/agents/executor/` for the observation-only Data Explorer contract;
- `src/application/evidence/` for observation admission;
- `src/agents/executor/hypothesis_analyst/` and
  `src/application/evaluation/` for protected proposal authorship;
- `src/application/governance/` for authority and decisions;
- `src/application/discovery/` for exact atomic materialization.

Focused behavioral verification is under
`tests/application/evidence/`, `tests/application/evaluation/`,
`tests/application/governance/`, and `tests/application/discovery/`.

Continue with [Protected evaluation](protected-evaluation.md),
then [Discovery governance and admission](discovery-governance-and-admission.md).
