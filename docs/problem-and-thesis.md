# Problem and thesis

Modern systems can generate analyses quickly. They can summarize a dataset,
suggest hypotheses, select methods, produce visualizations, and explain results
in fluent language. The difficult problem is no longer simply obtaining an
analysis. It is deciding what authority that analysis has, preserving the
provenance that makes it interpretable, preventing the wrong context from
shaping a conclusion, and knowing whether the result remains valid months
later.

Those problems become more severe in long-running, agent-assisted work. The
objective may evolve. Data may be cleaned or replaced. Provisional assumptions
may be corrected. Several specialists may contribute. Some investigations will
be inconclusive, and earlier findings may lose current validity without losing
their historical significance.

Faster generation does not solve any of this by itself. Without governed
research state, speed can produce more unsupported claims, more ambiguous
authority, and more stale material to retrieve.

The project response is:

> CogniEDA is validity-preserving research-state infrastructure.

This page explains why that infrastructure is needed. For a concise definition
and a multi-session example, begin with
[What is CogniEDA?](what-is-cognieda.md).

## Failure mode: conversation becomes state

A transcript is ordered by time, not by scientific meaning. It can contain a
research question, a user preference, a guessed data definition, a proposed
method, a tool result, a correction, and a final explanation within a few
adjacent turns. Later summaries may paraphrase the same idea repeatedly, omit a
qualification, or preserve both an original statement and its correction.

Treating that transcript as authoritative state creates several problems:

- meaning remains implicit in wording;
- paraphrases appear to be separate facts;
- contradictions may remain unresolved;
- old statements can look as current as new ones;
- ownership of each change is unclear;
- admission is not atomic; and
- lifecycle states such as proposed, approved, invalidated, or superseded are
  difficult to enforce.

Conversation remains valuable. It is where a human can express intent, review a
proposal, explain domain knowledge, or reject a result. But the durable research
record must state what each item means, what authority it has, and how it may be
used. Otherwise a later session has to infer governance from prose—and may
infer it differently.

## Failure mode: epistemic categories collapse

Research work depends on distinctions that ordinary text systems make easy to
erase.

An assumption is not an observation. An observation is not automatically
Evidence. Evidence is not its interpretation. A hypothesis is a commitment to
an evaluable question, not a finding. A Discovery is an evidence-bound claim,
not a synonym for an interesting sentence. A user preference can guide
presentation without becoming a scientific premise. A planning note can be
useful without being true.

When these categories collapse, authority leaks through language. A user says,
“Trial accounts are already excluded,” and the statement later appears beside
observed results as though it were verified. A model proposes that response
time drives churn, and the proposal is retrieved as prior knowledge. A summary
turns “the threshold was not met” into “there is no relationship.” Each change
may sound natural while silently strengthening the claim.

The risk is not merely imprecise terminology. It is contamination of the
reasoning process. Planning may legitimately use provisional assumptions to
choose work. Protected evaluation must not use those assumptions as empirical
support. Answering a question may refer to existing valid findings. Evaluating
a new finding must not treat those findings as substitute Evidence. Context
must therefore be eligible by epistemic type, not only relevant by topic.

## Failure mode: authority becomes ambiguous

Agent-assisted investigation involves several distinct acts:

1. A person expresses intent or makes a governance decision.
2. A Planner interprets the request and proposes coordinated work.
3. A specialist performs bounded, role-specific work.
4. Protected evaluation determines what admitted Evidence supports. Final
   scientific evaluation belongs to the Hypothesis Analyst or scientific
   investigation controller; it is an authority-bounded act, not a peer
   Evaluator agent.
5. Governance may approve, reject, or hold an eligible proposal. It may request
   correction, additional Evidence, or conflict review, but it does not revise
   scientific content directly. The appropriate scientific authority must
   create any revised proposal.
6. Application authority validates and admits only the authorized resulting
   state, then enforces its lifecycle.

If all participants appear able to “create” the same scientific object, the
system cannot explain where authority entered the record. The component that
produced a numerical result may also interpret it, approve its own wording, and
store that wording as truth. A Planner may be mistaken for the owner of
Evidence. A fluent model response may be mistaken for an authoritative change.

Proposal, execution, evaluation, governance, and admission are different acts
because they answer different questions. What should we do? What happened?
What does it support? Do we accept this exact outcome? May it become durable
state? Keeping those acts separate makes both human responsibility and system
behavior inspectable.

Model output therefore has bounded authority. It can propose work or return a
role-specific result. It cannot make itself scientifically authoritative, grant
itself approval, or unilaterally persist a new truth.

## Failure mode: provenance is incomplete

A result is not sufficiently traceable merely because its value was saved. A
reviewer must be able to reconstruct the chain that gives the value meaning:

- the research question and intended scope;
- the specific data state;
- the scientific contract and decision rule;
- the work that was requested and authorized;
- the execution that produced the observation;
- the exact analytical view used;
- the method, parameters, and relevant environment;
- the limitations and uncertainty; and
- the basis on which an outcome was evaluated.

Without that chain, “run the same analysis again” is ambiguous. The source data
may have changed. A filter may have been edited. A metric definition may differ.
A missing-data rule or random seed may be absent. Even a numerically correct
result cannot safely support later work if nobody can determine what it was a
result *of*.

Provenance is therefore part of scientific meaning rather than optional audit
decoration. It binds an observation to the conditions under which it was
produced and gives later validity changes something concrete to follow.

## Failure mode: stale validity enters active context

Historical truth-to-record and current scientific authority are not the same.

Suppose an analysis accurately recorded what happened on a particular data
state. Later, the team discovers that a cohort filter was wrong, a metric was
redefined, or an upstream data source was incomplete. Editing the old result
would falsify history. Deleting it would erase what the team previously knew
and why it acted. Leaving it active without qualification would contaminate
future reasoning.

The safe response is to preserve the historical record while changing its
eligibility for current use. Dependent Evidence, findings, and active-context
selections must be reviewable through their lineage. Protected evaluation must
exclude invalid state. Historical inspection may still show it, with the
validity event and reason visible.

This distinction is easy to lose in prose or similarity search. An invalidated
finding may remain the most direct textual answer to a later question. Unless
validity is checked before relevance ranking and again before use, stale
scientific authority can re-enter through an otherwise helpful retrieval step.

## Failure mode: continuity is mistaken for retrieval

Nearest-neighbor search, chat summarization, and transcript replay can all help
locate prior material. None can, by itself, reconstruct safe research state.

Similarity answers, “What text looks related?” It does not establish whether
the item is an assumption or Evidence, whether its data scope matches, whether
it was ever admitted, whether it has been superseded, or whether its type is
allowed in the current reasoning mode.

Summarization answers, “What compact story can represent this material?” It may
remove repeated identifiers, limitations, decision rules, rejected paths, or
the distinction between observed and inferred statements—the very details that
make a claim trustworthy.

Transcript replay preserves more detail but also restores noise: abandoned
plans, corrections, outdated results, failed reasoning, and temporary
instructions. A later agent then has to rediscover which parts remain active.

Continuity requires reconstruction, not recollection. The system must recover
what was intended, which data state was used, what work was authorized, which
observations were admitted, which outcomes were governed, what validity changes
occurred, and what may safely enter the next context. Retrieval can serve that
process only after structural eligibility and validity rules have done their
work.

## Failure mode: every execution becomes an insight

A system optimized to generate useful-looking output can feel pressure to turn
every analytical run into a conclusion. That pressure is scientifically
dangerous.

A method may be inappropriate. The necessary variable may not exist. The sample
may be too small. The protocol may be exhausted without discriminating between
plausible explanations. The result may fail to meet its decision rule. An
execution may be invalid, cancelled, or superseded before evaluation.

Forcing these cases into a Discovery manufactures confidence. It also removes
the information needed to decide what to do next: gather more data, refine the
question, change the protocol, or stop. A disciplined system needs typed ways
to remain incomplete.

An investigation may therefore end with insufficient Evidence, a not-testable
status, protocol exhaustion, invalidation, cancellation, or another governed
non-Discovery outcome. An inconclusive investigation is neither automatically
a Discovery nor automatically current scientific authority. A
`VALUABLE_INCONCLUSIVE` Discovery requires protocol completion, clear value, a
narrowly bounded claim, a DiscoveryProposal, governance, and authoritative
admission. Without those conditions the result remains a typed non-Discovery
outcome. In either case, “the available Evidence was insufficient to establish
the proposed association within this scope and method” can be useful; it is not
the same as “no association exists.”

Scientific restraint is not a lack of capability. It is the capability to
preserve the strongest conclusion the Evidence permits—and no stronger one.

## The thesis: govern research state

The design response can be stated more fully:

> Long-running agent-assisted investigation requires a governed research-state
> layer that separates semantic objects, workflow records, authority,
> provenance, validity, and active context.

Several consequences follow.

### Explicit typed state

Research intent, data state, assumptions, work state, scientific commitments,
Evidence, evaluated outcomes, durable findings, provenance, and context
selection need explicit meanings. Type is not cosmetic metadata; it determines
what an item may do, which lifecycle it follows, and which reasoning contexts
may admit it.

### Role and authority separation

The human, Planner, role-specific specialists, protected scientific evaluation,
governance, and application authority have different responsibilities. Their
outputs cross explicit boundaries. No role silently acquires observation,
interpretation, governance, and persistence authority at once. Protected final
evaluation belongs to the Hypothesis Analyst or scientific investigation
controller rather than to a separate canonical Evaluator agent.

### Immutable or append-oriented scientific lineage

When a data state or observed result changes, the historical scientific payload
should not be edited until it appears to have always been correct. A new state
and an explicit relationship preserve both the prior record and the current
authority. This supports reproducibility, correction, and later audit.

### Protected evaluation

The context allowed to support a new scientific claim must be constructed for
that purpose. It may use the relevant hypothesis, accepted data state,
analytical provenance, Evidence, method, parameters, decision rule,
uncertainty, and validity basis. It excludes planning assumptions, existing
Discoveries, raw conversation, failed reasoning, and unverified generated
views as inference premises.

### Typed non-completion

The system needs durable outcomes for work that does not justify a Discovery.
Inconclusive, insufficient, not-testable, exhausted, invalidated, and cancelled
states prevent absence of a positive finding from becoming a fabricated claim.

### Validity-aware retrieval

Eligibility by type, lifecycle, scope, and validity must precede relevance
ranking. Retrieval should distinguish active authority from historical context
and should fail closed when it cannot establish that an item is safe for the
requested use.

### Governed context construction

Different operations require different context. Planning may use active
assumptions. Protected evaluation may not. A user-facing answer may summarize
existing valid findings without allowing those summaries to become premises
for a new Discovery. Active context is therefore a governed projection over
research state, not a bag of relevant text.

### Restart-safe continuity

A new session should resume from durable identities, lifecycle state,
provenance, decisions, validity events, and a purpose-built active context. It
should not require an agent to recover scientific authority by rereading an
entire conversation.

Together, these consequences make validity preservation a property of the
research-state layer rather than a convention that every prompt and every
participant must remember to follow.

## The costs are deliberate

This thesis imposes real costs.

Research objects and transitions need more explicit contracts. Consequential
state passes through more admission steps. Specialist agents have less freedom
to reinterpret their role. Durable changes may take longer because authority,
freshness, and exact content must be checked. Governance adds operational work.
Ambiguous input is more likely to be rejected or returned for clarification.
Incomplete work may remain visibly incomplete instead of becoming a polished
conclusion.

The system also has to preserve more lineage and reason about validity across
dependencies. Context construction becomes stricter, and retrieval may prefer
a smaller safe result set over a larger plausible one.

These costs follow from the project's priority order:

1. conclusion validity and traceability;
2. context type safety;
3. multi-session continuity;
4. speed and convenience only after the first three.

If speed outranked validity, direct model output and mutable summaries would be
attractive shortcuts. If continuity outranked type safety, remembering more
related material would look like success. CogniEDA chooses the opposite: a
later session is useful only when what it resumes remains appropriately scoped,
typed, traceable, and valid.

## Stable design implications

The thesis does not prescribe one user interface, storage technology, model, or
analytical method. It does establish boundaries that any faithful design must
preserve:

- conversation can support interaction without becoming authoritative research
  state;
- assumptions can guide planning without becoming Evidence;
- observation, evaluation, governance, and durable admission remain distinct;
- Evidence stays bound to data state and analytical provenance;
- a Discovery requires Evidence and an explicit scope and validity basis;
- non-Discovery outcomes remain explicit governed workflow results;
- historical records can remain truthful while losing current authority;
- validity and type eligibility govern what enters active context; and
- continuity reconstructs safe research state instead of replaying a transcript.

Detailed object definitions belong in the research-state documentation.
Complete role and authority contracts belong in architecture. Scientific
lifecycle, validity propagation, and context construction need their own
focused pages. Present capability and maturity belong in status documentation.
Keeping those details separate lets this thesis remain stable even as the
underlying system evolves.

Return to [What is CogniEDA?](what-is-cognieda.md) for the concise model, or to
the [documentation index](index.md) for the full reading journey.
