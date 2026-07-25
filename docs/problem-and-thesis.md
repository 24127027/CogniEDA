# Problem and thesis

Analytical work produces more than code and prose. It produces research intent,
dataset state, planning constraints, test contracts, observed results,
interpretations, decisions, active context, and invalidation history. When those
roles are stored as undifferentiated text, a project can remain readable while
becoming scientifically unsafe.

CogniEDA's response is to govern the state of an investigation:

> CogniEDA is validity-preserving research-state infrastructure.

The design gives first priority to conclusion validity and traceability, second
to context type safety, and third to multi-session continuity. This page
explains the practical failures behind that priority order and the cost of the
response.

> **Implementation status:** The guarded in-process scientific path is
> **Implemented** and **Verified on SQLite**. The complete user-facing Planner,
> dataset, SessionFrame, and product workflows are **Partially implemented** or
> **Unsupported**, as identified in the relevant sections below.

The running example asks whether longer first-response time is associated with
90-day churn in a defined small-business cohort.

## Conclusions detached from exact dataset state

A conclusion such as “response time predicts churn” is unsafe when nobody can
identify the dataset version, cohort definition, or preprocessing state on
which it was based. A later refresh may change rows, column meanings, or
missing-data treatment while the sentence remains unchanged.

A notebook can preserve the code that once loaded a file, but the file path may
now resolve to different bytes. A chat transcript can preserve the analyst's
description, but not make that description a stable data identity. A generic
retrieval system can find the sentence without knowing whether its data
authority is still active.

CogniEDA gives each profiled dataset state a durable `DataProfile`. Analytical
work binds to a specific accepted profile, and a changed dataset requires a new
profile rather than rewriting the old one. When the old profile is invalidated
or superseded, dependent scientific state can be marked accordingly and
excluded from active retrieval.

The tradeoff is version proliferation. Profiles need lifecycle policy,
supersession links, and retrieval filters. That is more work than updating one
mutable “current dataset” record, but it keeps the historical conclusion
attached to the state that actually supported it.

## Analytical results without reproducible provenance

A result can be numerically correct and still be unusable if its data view,
method, parameters, execution attempt, and environment are unclear. Re-running
“the same analysis” may silently mean a different filter, seed, or code path.

Notebook cell order and logs can help, but they are not a durable contract.
Chat history can say that a regression was run without proving which approved
contract produced which result. A summary often removes the details first
because they look repetitive.

CogniEDA separates the test contract from execution provenance. A `Hypothesis`
states what will be tested. `AnalysisFrame` records identify the data view, and
`ExecutionRun` records identify the attempt. `Evidence` binds its observed
result back to that lineage. Protected evaluation reconstructs the lineage from
durable state instead of accepting a caller-supplied narrative.

The current reproducibility envelope is **Partially implemented**: it captures
the load-bearing lineage, method, parameters, and selected code/environment
references, but it is not yet a general reproducibility system. More complete
environment and artifact capture will increase storage and operational
complexity.

## Assumptions silently influencing inference

Planning often needs provisional beliefs. In the running example, the team may
assume that each row represents one account-month or that trial accounts are
already excluded. Those beliefs can help identify useful Tasks. They must not
become empirical premises merely because they appeared earlier in the
conversation.

Prompt instructions such as “treat assumptions carefully” are fragile.
Summaries tend to remove the distinction between “the user believes” and “the
analysis observed.” Similarity retrieval can inject a relevant Assumption into
the same context as Evidence.

CogniEDA quarantines `Assumption` by context role. Planning context may include
active Assumptions. The protected Discovery synthesis bundle has no Assumption,
chat, generic context, or existing Discovery field. The Analyst receives the
closed bundle without tools or message history. A new Discovery may later be
compared with an Assumption to flag a contradiction, but the Assumption is not
an inference premise.

This is **Implemented** for the protected evaluation path. The tradeoff is that
planning and conclusion evaluation need different context builders and
contracts. Information cannot flow between them merely because it is
convenient.

## Chat summaries erasing scope and uncertainty

A useful summary compresses detail. A scientific claim can become misleading
when compression removes the cohort, method, uncertainty, decision rule, or
limitations that bound it.

For example, “the test was not significant” can easily become “response time
does not affect churn.” The second statement is stronger. A chat summary has no
built-in obligation to preserve the difference.

CogniEDA represents a Discovery with structured claim, scope, epistemic status,
uncertainty, validity basis, limitations, and invalidators. Schema validation
rejects unqualified absence wording in analytical result and claim fields, and
protected evaluation requires a fail-to-reject result to remain inconclusive or
insufficient-evidence rather than supported or contradicted.

The tradeoff is less freedom to store polished prose as the sole source of
truth. Generated summaries still have value, but they are views over governed
state and may need regeneration when the underlying state changes.

## Stale conclusions remaining active after Evidence changes

Suppose the team later discovers that the churn Evidence used an incorrect
cohort filter. Deleting the old result destroys history. Leaving its Discovery
active contaminates future planning and answers.

Notebook annotations and chat corrections depend on people reading the right
later note. A vector index may continue returning the original conclusion
because it is still semantically relevant. A best-effort asynchronous update
can leave some dependent records current and others stale.

CogniEDA preserves the old state and records an authorized validity event. The
supported propagation path can update the source validity state and dependent
Evidence, evaluation controls, admission claims, Discoveries, Hypotheses, Task
review signals, and SessionFrames in one transaction. Active retrieval excludes
invalidated or deprecated Discoveries and superseded frames, while explicit
historical reads remain possible.

This behavior is **Verified on SQLite**. The tradeoff is a dependency graph,
compare-and-set transitions, immutable event records, replay verification, and
more complicated retrieval policy. Cross-database and distributed guarantees
are **Unsupported**.

## Indiscriminate retrieval contaminating reasoning

Textual relevance is not scientific eligibility. A rejected Task, a stale
Discovery, an active Assumption, a generated summary, and valid Evidence can all
contain the same keywords. Retrieving them into one prompt gives them an
accidental equivalence.

A generic vector search answers “what sounds related?” It does not necessarily
answer “what is valid in this context role, lifecycle state, data scope, and
authority boundary?”

CogniEDA applies type and lifecycle policy before relevance scoring. Planning,
answer, conclusion, and Discovery synthesis are distinct context modes. Bounded
Discovery retrieval filters invalid and excluded state, respects profile scope,
and separates items eligible to motivate work from items that are merely
relevant for review. The current scorer is deterministic lexical overlap, not a
persistent semantic index.

The tradeoff is lower recall and more policy code at the current scale.
Deterministic lexical retrieval is a reasonable local optimum while the
candidate pool is small and inspectable. A richer index should be revisited
when candidate volume or vocabulary variation makes bounded lexical retrieval
insufficient, but it must remain downstream of structural eligibility.

## Parent-task summaries mistaken for scientific claims

A parent Task may organize several analytical children. A summary of their
combined results can be useful, but it does not represent one test contract,
one Evidence set, or one validity basis.

Notebook narratives and agent summaries often turn the organizing question
into a single concluding paragraph. Persisting that paragraph as a Discovery
would bypass the one-terminal-Task scientific lineage and obscure which child
Evidence supports which statement.

CogniEDA permits only terminal analytical Tasks to generate Hypotheses and
Discoveries. Parent Tasks do not produce Discoveries. Their answers belong in a
`GeneratedView`: a regenerable output assembled from valid child Discoveries
for a particular question.

`GeneratedView` is a **Design target**; the current Planner answer path is
**Partially implemented** and does not provide the complete generated-view
workflow. The tradeoff is that parent-level answers may need regeneration and
cannot serve as authoritative scientific knowledge. That cost protects the
lineage of the underlying claims.

## Retries producing duplicate or conflicting durable state

Execution, evaluation, and admission may be retried after timeout, process
restart, or uncertain acknowledgement. Without durable identity and fencing,
two workers can create duplicate Evidence, publish different proposals for one
attempt, or partially complete a Discovery chain.

A notebook rerun or generic queue retry does not automatically distinguish an
exact replay from changed content. “Run it again” can overwrite prior output or
append a second, incompatible result.

CogniEDA uses durable attempt identities, idempotency keys, content digests,
lease epochs, fencing tokens, deterministic artifact identities, unique
constraints, and compare-and-set transitions. Exact replay may return the
committed winner; changed content conflicts. Evidence admission and Discovery
admission group their respective multi-record state changes into application-
owned transactions.

These paths are **Verified on SQLite**. The tradeoff is substantial operational
state and more failure modes to test. External Data Explorer effects remain
at-least-once, so a future distributed worker design must revisit end-to-end
idempotency without weakening the existing admission boundaries.

## Long-running projects losing the reasoning chain

Months into a project, a team may remember the conclusion but forget why a Task
was opened, which Assumption was provisional, which Evidence was superseded, or
what another session should examine next.

Raw transcripts are complete but unwieldy. Summaries are compact but lossy.
Notebook history is organized by execution order rather than the epistemic role
of each artifact. Generic long-term memory may retain both obsolete and current
state without a reliable distinction.

CogniEDA uses typed durable objects for research state and `SessionFrame`
snapshots for active context, checkpoints, and handoffs. Frames can expose pins,
exclusions, warnings, stale markers, dead ends, and relevant object references.
They are projections over governed state, not replacements for the underlying
objects and not protected inference bundles.

The complete session-resume and item-governance product experience is
**Partially implemented**. The tradeoff is explicit frame construction,
supersession, and scope policy. The redesign trigger is a multi-user or
multi-branch product in which “latest active frame” is no longer an adequate
cardinality rule.

## Why Evidence and Discovery remain separate

Several failure modes above converge on one decision: observed output and a
scientific claim must not be the same record.

The Data Explorer has observation authority. The Hypothesis Analyst has
proposal-authoring authority inside a protected context. Governance has
decision authority. The application has exact materialization authority. This
separation prevents the component that produced a number from also deciding
what it means, approving that meaning, and storing it as truth.

The additional proposal, decision, and admission lifecycle is expensive. It is
also where CogniEDA can preserve exact wording, reject stale authority, and
atomically complete the terminal scientific chain.

## Why immutable data and Evidence state matter

`DataProfile` and `Evidence` scientific payloads are immutable. Correcting
either means creating a new record and using authorized invalidation or
supersession metadata on the old record; it does not mean editing history until
the old conclusion appears correct.

This preserves the answer to “what did the project know at that time?” It also
creates supersession chains and makes active retrieval more demanding. Those
costs are preferable to provenance that changes underneath an existing claim.

## Current boundary and future pressure

The current source provides an in-process foundation and **Verified on SQLite**
transaction paths. It does not provide a production CLI, API, worker,
authentication adapter, concrete Data Explorer, or distributed deployment.

The architecture should be revisited when one or more of these conditions
become real requirements:

- independent services must coordinate scientific commits;
- multiple users or branches need explicit SessionFrame scope and concurrency;
- retrieval candidate volume requires an index beyond bounded relational and
  lexical search;
- supported databases extend beyond SQLite;
- reproducibility requires container, code, environment, and artifact capture
  beyond the current provenance envelope;
- generated parent-level answers need durable caching without becoming
  scientific knowledge.

Revisiting a local optimum does not mean discarding the invariants. Any new
design must still preserve conclusion traceability, context type safety,
specialist authority separation, and historical validity.

### Implementation orientation

The principal source boundaries supporting this page are
`src/schemas/`, `src/application/evidence/`,
`src/application/evaluation/`, `src/application/discovery/`,
`src/application/validity/`, and `src/memory/`. Focused behavioral evidence
lives under `tests/application/`, `tests/memory/`, and `tests/e2e/`.
