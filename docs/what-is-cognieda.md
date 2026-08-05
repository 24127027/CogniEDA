# What is CogniEDA?

> CogniEDA is validity-preserving research-state infrastructure.

In plain language, CogniEDA is a foundation for analytical and scientific work
that must remain understandable and trustworthy across many actions, people,
agents, and sessions. It keeps the state of an investigation explicit: what the
research is trying to establish, which data state is in scope, what has only
been assumed, what work was authorized, what was observed, what may be
concluded, and whether an earlier finding is still safe to use.

This matters because a conversation can help people and agents reason without
being a reliable record of research authority. A transcript tells us what was
said. It does not reliably tell us whether a sentence is a planning idea, a
user-supplied assumption, an observed result, an evaluated claim, or a finding
that has since become stale. CogniEDA addresses that gap by treating research
state as governed state rather than as remembered prose.

The project is especially motivated by hypothesis-driven exploratory data
analysis, where questions, data quality, and analytical direction evolve
together. Its model is broader than one test or one linear sequence, however.
The aim is not to automate a path from a file to an insight. The aim is to make
long-running investigation traceable, restrained, and safe to resume.

## A multi-session investigation

Consider a team investigating whether first-response time is associated with
90-day customer churn.

In the first session, the team sets an objective: identify service conditions
that are meaningfully associated with churn for small-business customers. The
available data covers the previous year, but its cohort definition and time
fields still need review. A team member believes that trial accounts have
already been excluded. That belief can guide the next checks, but it is an
assumption, not an observed fact.

In a later session, the accepted data state is clear enough to investigate a
specific hypothesis about first-response time. The team agrees on the cohort,
variables, method, decision rule, and expected result. Bounded analytical work
then produces Evidence: an observed result tied to that data state and
analytical contract. Protected evaluation may support a scoped finding, may
contradict the hypothesis, or may determine that the available Evidence is
insufficient.

Suppose the completed protocol produces a clearly valuable but inconclusive
outcome. This does not automatically create a Discovery. In this case, the
scientific investigation produces a narrowly scoped `DiscoveryProposal`
stating only that the available Evidence did not establish the proposed
association under the admitted data, method, decision rule, and scope.
Governance approves that exact proposal, and application authority admits it
as a `VALUABLE_INCONCLUSIVE` Discovery.

Had those conditions not been met, the investigation would instead have ended
with a typed non-Discovery outcome. That path could still preserve the useful
outcome without converting it into an admitted scientific claim or the
stronger claim that no relationship exists.

Months later, the cohort logic is found to have included trial accounts after
all. The admitted Discovery remains historical truth-to-record: it truthfully
describes what was observed and admitted at the time. But it loses current-use
eligibility for the intended cohort. The next session must see both facts—the
history and the loss of current validity—rather than retrieving only the most
fluent old summary.

This is the continuity CogniEDA is designed to provide. It is not transcript
replay. It is reconstruction of the governed state needed to answer: What were
we trying to learn? Which data did we use? What was authorized? What did we
observe? What conclusion, if any, was justified? What changed? What is safe to
use now?

## What the system preserves

CogniEDA keeps several categories of research state distinct because they have
different meanings and different authority.

- **Research intent** states the outcome being pursued and the boundaries of
  the investigation.
- **Planning constraints** include assumptions and provisional beliefs that may
  guide what to examine next without becoming scientific premises.
- **Data state** identifies the particular profiled and accepted state of data
  to which later work applies.
- **Scientific commitments** state what will be investigated and under which
  analytical conditions.
- **Observations and Evidence** record what bounded analytical work produced,
  with the provenance needed to interpret it.
- **Evaluated outcomes** record whether the work supports a finding, contradicts
  it, remains inconclusive, cannot be tested, is invalid, or ends in another
  governed state.
- **Durable findings** express evidence-bound claims with explicit scope and a
  basis for deciding when they remain valid.
- **Validity state** distinguishes what remains true-to-record from what is
  currently eligible for reuse.
- **Active context** selects the smallest safe working set for the current kind
  of reasoning.

The specialized terms carry deliberate boundaries. An **Assumption** is a
planning constraint; it does not become Evidence because a user stated it or a
model repeated it. **Evidence** is an observed analytical result, not the
interpretation of that result. A **Discovery** is a governed, evidence-bound
claim with explicit scope and validity basis, not a polished paragraph or a
reward for completing an analysis.

Not every investigation produces a Discovery. Work may end with insufficient
Evidence, a not-testable status, an exhausted protocol, invalidation,
cancellation, or another typed non-Discovery outcome. Even a valuable
inconclusive result becomes a Discovery only after protocol completion,
narrowly scoped proposal, governance, and authoritative admission. These
outcomes are part of disciplined research state, not failures to generate
content.

## What CogniEDA is not

CogniEDA may use conversation, models, analytical tools, retrieval, and
specialist agents, but none of those defines its scientific authority.

It is not primarily a chatbot or a conversational-memory product. Conversation
is an interaction surface and a source of proposals; it is not the
authoritative research record. Remembering more dialogue would preserve stale,
contradictory, and differently typed statements alongside valid ones.

It is not an autonomous scientist and does not treat model confidence as
scientific confidence. A model can help interpret intent or propose work, but a
persuasive response cannot admit itself as durable scientific knowledge.

It is not a generic multi-agent framework. Specialist cooperation matters, but
the defining problem is the preservation of research meaning and validity when
authority changes hands.

It is not a vector-database wrapper. Similarity can help rank eligible material,
but textual relevance cannot determine whether an item has the right type,
scope, lifecycle, and validity for a protected reasoning context.

It is not an unrestricted data-analysis agent. CogniEDA deliberately limits
what may execute, what may influence an evaluation, and what may become durable
state. Those limits protect the difference between exploration and justified
conclusion.

## A high-level operating model

At a conceptual level, work flows through:

```text
human intent
  -> governed planning
  -> bounded specialist work
  -> authoritative admission
  -> protected evaluation
  -> governed outcome
  -> validity-aware continuity
```

The human interacts through a Planner. The Planner coordinates research work
and proposes governed changes. Specialist executors perform bounded,
role-specific work. Application authority services own durable identity,
admission, transactions, lifecycle transitions, and validity-preserving
persistence. Model output remains a proposal or a bounded result until the
appropriate authority admits it.

This separation matters because proposal, execution, evaluation, governance,
and durable admission are different acts. No participant gains all of those
powers merely by producing plausible text or a numerical result.

CogniEDA applies its priorities in a strict order:

1. **Conclusion validity and traceability** come first. A claim must remain
   connected to the state and Evidence that justify it.
2. **Context type safety** comes second. Relevant but ineligible material must
   be kept out of protected reasoning.
3. **Multi-session continuity** comes third. Resumption must reconstruct valid,
   governed state rather than replaying everything that was said.
4. **Speed and convenience** matter only after the first three are protected.

Remembering an invalid claim more efficiently is not progress. Producing a fast
answer from contaminated context is not continuity. The priority order is what
makes the operating model coherent.

## Why this model matters

Explicit research state improves reproducibility because a result remains tied
to the data state, analytical conditions, and provenance that produced it. It
improves traceability because assumptions, observations, evaluated claims, and
validity changes do not blur into one narrative. It supports scientific
restraint because incomplete or inconclusive work can remain exactly that.

The same model makes resumption safer. A later session can receive the smallest
valid context for its purpose, including warnings and invalidations, without
trusting an entire transcript. It also makes human-agent collaboration more
reliable: people can govern consequential changes while specialists operate
within explicit bounds and application services preserve the durable record.

The result is not a promise that every investigation will be conclusive. It is
a promise of a stronger discipline: the system should preserve what is known,
how it is known, where it applies, what remains uncertain, and when it may no
longer be used.

## Where the detail belongs

This page introduces the project model. Detailed research-state object
definitions belong in the research-state documentation. Complete authority
contracts belong in the architecture documentation. Scientific lifecycle,
validity, and context construction receive their own focused explanations.
Present capability and maturity belong in status documentation rather than in
this conceptual entry point.

Read [Problem and thesis](problem-and-thesis.md) for the failure modes that make
this infrastructure necessary. Continue with the
[research-state foundation](concepts/research-state/index.md), consult the
[object catalog](reference/object-catalog.md), or return to the
[documentation index](index.md).
