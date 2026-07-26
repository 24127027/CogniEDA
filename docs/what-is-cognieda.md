# What is CogniEDA?

A serious analytical project rarely fails because nobody can produce a chart or
run a statistical test. It fails because, weeks later, nobody can answer the
questions that make a conclusion trustworthy:

- Which exact dataset version was used?
- Which rows, columns, method, parameters, and decision rule produced the result?
- Was a statement observed, assumed, inferred, or merely summarized?
- Is the conclusion still valid after the data or provenance changes?
- What should another session retrieve, and what must it keep out of the next
  inference?

Notebooks, chat transcripts, and search indexes can preserve pieces of this
history. They do not, by themselves, preserve the scientific role, lifecycle,
authority, and validity of each piece.

CogniEDA addresses that problem by treating an investigation as governed
research state.

## The project in one sentence

> CogniEDA is validity-preserving research-state infrastructure.

It gives durable identity to the parts of an investigation that must survive
across operations and sessions, keeps observations separate from claims, and
controls which kinds of state may enter each kind of reasoning.

This makes CogniEDA:

- infrastructure for analytical investigations whose conclusions must remain
  traceable;
- a governed state model for research intent, workflow, data state, test
  contracts, observations, claims, and active context;
- a boundary between scientific specialists, user governance, and durable
  materialization;
- a foundation for multi-session continuity built from typed state rather than
  remembered conversation.

CogniEDA is not:

- a generic EDA chatbot;
- a long-memory chat assistant;
- a vector-store wrapper;
- an autonomous scientist;
- a generic multi-agent framework;
- a notebook-history summarizer.

Those tools may help a person work, but they do not establish what is allowed to
become durable scientific knowledge.

## Why validity comes before memory

CogniEDA has three priorities, in this order:

1. **Conclusion validity and traceability.** A durable claim must remain bound to
   the exact data state, test contract, observed Evidence, method, uncertainty,
   scope, and invalidation conditions that justify it.
2. **Context type safety.** Planning material, assumptions, prior claims,
   generated summaries, and stale state must not enter a protected conclusion
   simply because they are textually relevant.
3. **Multi-session project continuity.** Another session should be able to
   resume from compact governed state without replaying or trusting the entire
   conversation.

This order matters. A system that remembers an invalid conclusion more reliably
has not improved the research process. CogniEDA pursues continuity as a
consequence of preserving valid, typed, governable state.

## Retained conversation is not retained research state

A conversation records what was said. Governed research state records what a
statement *is* and what authority it has.

For example, these sentences may look similar in a chat transcript:

- “Longer support response time probably increases churn.”
- “The approved analysis will test response time against 90-day churn.”
- “The fitted model returned an estimated effect and uncertainty interval.”
- “Within the stated cohort and method, the available Evidence was
  insufficient to establish an association.”

CogniEDA treats them as different kinds of state:

- the first may be an `Assumption` that can guide planning but cannot support a
  conclusion;
- the second belongs to a `Task` and its `Hypothesis` test contract;
- the third is `Evidence`, an observed analytical result;
- the fourth may become a `Discovery`, but only after protected evaluation and
  governance.

A chat summary can compress all four into one persuasive paragraph. CogniEDA's
model is designed to prevent that compression from changing their authority.
The cost is more explicit schemas, lifecycle rules, admission checks, and
transaction infrastructure. That cost is deliberate: scientific roles should
not depend on wording conventions alone.

## The investigation chain

The canonical investigation chain is:

```text
Research Objective
  -> Task
  -> Hypothesis
  -> AnalysisFrame / ExecutionRun
  -> Evidence
  -> Discovery
  -> GeneratedView
```

Each step answers a different question:

- `Objective`: What research outcome are we pursuing?
- `Task`: What work has been proposed, approved, decomposed, or completed?
- `Hypothesis`: What exact test contract will one terminal analytical Task run?
- `AnalysisFrame` and `ExecutionRun`: Which data view and execution attempt
  produced the observation?
- `Evidence`: What did the analysis observe?
- `Discovery`: What scoped claim is justified by that Evidence?
- `GeneratedView`: How should valid state be summarized or presented for the
  current question?

The arrows are not a license to collapse the objects. In particular, execution
does not create a Discovery, and a generated answer does not become scientific
knowledge merely because it is useful.

## A running example

Suppose a retention team asks:

> Within the 2025 small-business subscription cohort, is longer first-response
> time associated with 90-day churn?

The project may create an `Objective` to understand actionable churn drivers. A
parent `Task` may organize several possible drivers. One terminal analytical
`Task` narrows the work to first-response time and churn for a specific accepted
`DataProfile`.

After the user approves the exact analytical contract, one `Hypothesis` binds
the variables, cohort, method, parameters, decision rule, and expected Evidence.
A configured Data Explorer observes the approved analysis and returns typed
results. The application has already admitted the `ExecutionRun` with the
approved contract; after a successful result, Evidence admission materializes
the `AnalysisFrame` and immutable `Evidence`.

Assume the observed result does not meet the approved threshold. The Evidence
might say:

> The fitted analysis returned the recorded effect estimate and uncertainty;
> the decision threshold was not met.

That is an observation. It is not yet the research conclusion.

Protected evaluation may propose a Discovery such as:

> Available Evidence is insufficient to establish an association between
> first-response time and 90-day churn within the 2025 small-business cohort
> using the approved method and decision rule.

The wording preserves scope, method, and uncertainty. It does not turn a
fail-to-reject result into proof that no relationship exists. Governance may
approve, reject, or cancel that exact proposal. Only an approved proposal can be
materialized as a durable Discovery.

This example is reused in the other Phase 1 documents.

## Evidence is not Discovery

`Evidence` is the observed analytical result. It records what the approved
execution produced, with method and provenance.

`Discovery` is the evidence-bound claim admitted after protected evaluation and
governance. It carries structured claim, scope, epistemic status, uncertainty,
validity basis, limitations, and invalidators.

The distinction protects against several failures:

- an executor interpreting its own output as truth;
- a result summary becoming more certain as it is rewritten;
- governance approving one claim while the application stores another;
- a later data or provenance change leaving an unsupported claim active.

The tradeoff is an additional lifecycle: observed output must be admitted,
evaluated, governed, and atomically materialized. CogniEDA accepts that
complexity because observation and interpretation have different scientific
authority.

## SessionFrame is user-governed active context, not long-term memory

A `SessionFrame` is a user-governed active-context projection for a particular
investigation moment. It can carry an Objective snapshot, relevant profiles,
active Tasks, planning Assumptions, Evidence and Discovery summaries, user pins
and exclusions, warnings, dead ends, and handoff state. Persisted frame content
is append-oriented: changing the active context creates a successor snapshot
rather than rewriting the selected content of the earlier frame. Lifecycle
metadata can later mark an older frame superseded.

It is not an unrestricted archive and it is not the protected conclusion
context. A frame may contain Assumptions for planning, while the protected
evaluation bundle excludes them structurally. A frame may point to a Discovery
for answering or planning, while a new Discovery cannot use an existing
Discovery as its inference premise. Objects selected through a frame retain the
authority rules of their own epistemic types; neither the frame nor a pin makes
an item scientific Evidence.

User governance matters because relevance is not purely a similarity score. A
user may need to pin a valid item, exclude an irrelevant one, approve a proposed
Task, approve an execution contract, or accept or reject a proposed claim.
Current source supports several of these durable approval and frame mechanisms,
but the complete user-facing SessionFrame governance experience is only
**Partially implemented**.

The tradeoff is that context construction becomes explicit and mode-specific.
The benefit is that “remember this” cannot silently become “use this as
scientific evidence.”

The full concept is owned by
[SessionFrame and active context](session-frame-and-active-context.md).

## Current maturity

The current repository is an in-process Python foundation, not a deployed
analytical product.

- **Implemented:** the typed core research objects; guarded Planner operation
  and execution approvals; execution provenance and Evidence admission;
  protected evaluation; proposal governance; atomic Discovery admission;
  validity propagation; bounded Discovery retrieval; and SessionFrame
  snapshots.
- **Verified on SQLite:** current atomicity, replay, fencing, and concurrency
  guarantees. No cross-database guarantee is claimed.
- **Partially implemented:** natural-language Planner branches, governed
  dataset acceptance, SessionFrame governance, and session resume.
- **Known deviation:** the Planner currently authors the operational analytical
  contract; the longer-term authority model assigns scientific
  operationalization to the Hypothesis Analyst.
- **Unsupported:** a production CLI, HTTP API, worker or daemon, production
  authentication implementation, concrete Data Explorer, default production
  Analyst model adapter, distributed execution, and multi-user deployment.
- **Deferred:** executable DVC integration, governed cleaning, Graph Miner,
  persistent semantic indexing, and Evidence Cache.

The current paths are enough to verify important scientific boundaries, but not
enough to claim a complete product workflow.

## Where to go next

Read [Problem and thesis](problem-and-thesis.md) for the failure modes behind the
design. Then read [Research-state model](research-state-model.md) for the
objects and lifecycle boundaries, followed by
[From question to Discovery](from-question-to-discovery.md) for the complete
conceptual investigation. The authority chain continues in
[Scientific authority](scientific-authority.md),
[Protected evaluation context](protected-evaluation-context.md), and
[Governance and Discovery admission](governance-and-discovery-admission.md).
The focused workflow is
[From execution to Discovery](from-execution-to-discovery.md). Active-context
continuity continues in
[SessionFrame and active context](session-frame-and-active-context.md),
[Retrieval and context type safety](retrieval-and-context-type-safety.md), and
[Context reconstruction and continuity](context-reconstruction-and-continuity.md).
The running example continues in
[From research state to active context](from-research-state-to-active-context.md).

### Implementation orientation

Readers who later need to verify the high-level status can begin with
`src/schemas/`, `src/application/`, `src/memory/`, and the focused tests under
`tests/application/`, `tests/memory/`, and `tests/e2e/`. These locations support
the explanation; they are not prerequisites for understanding it.
