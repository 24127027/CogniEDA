# Discovery governance

A protected evaluation may propose an evidence-bound claim. It cannot admit
that claim as a Discovery. CogniEDA keeps proposal authorship, governance, and
durable admission as separate acts.

This page defines the **target design** for DiscoveryProposal review,
correction and additional-Evidence loops, typed termination, and Discovery
admission.

## DiscoveryProposal is not Discovery

A `DiscoveryProposal` is a durable non-FCO candidate produced by protected
evaluation. It binds the proposed outcome, exact claim, scope, validity basis,
admitted Evidence, and authoritative scientific lineage.

It remains a proposal until governance authorizes the exact version and
application authority successfully admits it. Presentation, persistence of the
proposal, or a positive evaluation label does not turn it into a Discovery.

## Governance decisions

Governance may:

- approve;
- reject;
- hold;
- request correction;
- request additional Evidence;
- request conflict review.

Governance does not rewrite scientific content. A requested correction returns
to Hypothesis Analyst or the scientific investigation controller, which must
produce a new traceable proposal version. A request for additional Evidence
returns through Evidence obligations, admitted EvidenceRequest, Data Explorer,
and Evidence admission before protected evaluation is repeated.

Conflict review may gather eligible contradiction and validity information. It
does not authorize Graph Miner, governance, or the Planner to edit the
Hypothesis, protocol, evaluation, or proposed claim.

## Discovery admission

After approval, application authority validates and atomically admits the
exact proposal only when all required conditions hold. A Discovery must bind
to:

- the Hypothesis;
- admitted eligible Evidence;
- the exact claim;
- scope;
- validity basis;
- governance;
- authoritative scientific lineage.

Admission also enforces exact proposal/decision identity, Objective scope,
allowed Discovery outcome, active protocol and Evidence eligibility, and
cardinality. Governance approval authorizes the transition; it does not perform
the write. Application admission performs the write; it does not author or
revise the claim.

## Cardinality

```text
Hypothesis
  -> at most one Discovery
```

The upper bound prevents competing Discoveries from being admitted for one
Hypothesis. It does not require a Discovery. A parent Task produces no
Discovery, and an investigation ending in rejection, hold, or typed
non-completion does not receive a fabricated placeholder claim.

## Non-Discovery termination

Not-testable, insufficient-data, insufficient-Evidence, protocol-exhausted,
out-of-scope, cancelled, invalidated, superseded, and replan-cancelled paths
remain traceable scientific-investigation endings. They may support planning,
reporting, or later successor work, but they are not Discoveries.

Held and correction-requested proposals remain pending governance state rather
than terminal scientific claims. Rejected proposals remain historical
truth-to-record but are not eligible for presentation as admitted Discovery.

## Correction after admission

Discovery content is evidence-bound and cannot be silently rewritten after
admission. New observations require new Evidence; changes to current-use
eligibility require an explicit validity or lifecycle transition; materially
different scientific work requires the appropriate successor lineage. These
acts preserve the original truth-to-record.

## Implementation status

**Design target with partial repository guards.** Current source has immutable
Discovery content, requires Evidence references and a validity basis, excludes
Assumptions through a model guard, and enforces a repository-level one-
Discovery-per-Hypothesis constraint. It does not implement DiscoveryProposal,
GovernanceDecision, exact proposal authorization, allowed canonical outcomes,
or atomic application-authority Discovery admission across the complete
scientific lineage.
