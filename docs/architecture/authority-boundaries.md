# Authority boundaries

CogniEDA separates authority so that no useful model output, execution result,
or persistence operation can silently acquire a stronger epistemic role. This
page is the primary owner of the architecture authority model.

The boundaries below are target architecture. Persistence may preserve an
authoritative record, but persistence alone never confers scientific
authorship.

## Authority taxonomy

| Authority | Canonical holder | May decide or perform | Cannot acquire by implication |
| --- | --- | --- | --- |
| human authority | Human through the Planner boundary | intent, approval policy, consequential plan approval, clarification, rejection, and requested revision | executor access, scientific authorship, or admission mechanics |
| planning authority | Planner | Objective coordination, consultation, PlanRevision and Task DAG proposals, routing, replanning, SessionFrame and GeneratedView coordination | scientific operationalization or Evidence creation |
| execution authority | bounded specialist under an admitted work contract | perform the exact role-specific operation and return a bounded result | admission, governance, or permission to expand scope |
| scientific authority | Hypothesis Analyst or the scientific investigation controller | feasibility, Hypothesis and protocol content, Evidence obligations, protected evaluation, and exact scientific proposal content | dataset access, governance self-approval, or persistence authority |
| governance authority | authorized human or policy-governed review boundary | approve, reject, hold, or request correction, more Evidence, or conflict review | rewriting scientific content or making a proposal durable |
| admission authority | application authority | validate the exact contract and apply the authorized durable transition | authorship of the admitted content |
| persistence authority | application authority | transaction ownership, durable write ordering, idempotency, replay, and recovery | scientific interpretation or governance judgment |
| validity-transition authority | authorized validity boundary applied by application authority | change current-use eligibility while preserving truth-to-record | rewriting admitted Evidence or Discovery content |

## Human authority and approval modes

The human interacts with the Planner only. The Planner explains proposals,
collects decisions, and returns valid results or blockers. Data Explorer,
Hypothesis Analyst, and Graph Miner do not ask the human for approval or
clarification directly.

Approval policy exists only at the Planner-human boundary:

| Mode | Meaning |
| --- | --- |
| `ALWAYS_ASK` | every governed proposal within the configured scope requires an explicit human decision |
| `POLICY_GUARDED` | explicit policy decides which proposals require a human decision and which may proceed automatically |
| `ALWAYS_ACCEPT` | eligible proposals within the explicitly configured scope may proceed without an interactive decision |

The architectural default is `POLICY_GUARDED`. Initial plan approval is
required unless an explicit policy says otherwise. A policy may remove an
interaction step; it does not remove typed validation, eligibility checks,
governance requirements, or admission authority.

## Planning authority

The Planner is the control plane. It owns Objective coordination, planning
consultations, `PlanRevision` and Task DAG proposals, routing, replanning,
approval coordination, SessionFrame and GeneratedView coordination, restart
and resume orchestration, and high-level work synthesis.

The Planner does not define a Hypothesis statement, method, statistical test,
parameters, decision rule, seed, variable bindings, `InvestigationPlan`,
`InvestigationProtocol`, protocol revision, Evidence obligation, or protected
scientific evaluation. It may propose that scientific work is needed, but only
scientific authority may operationalize that work.

Planner consultation with Data Explorer or Graph Miner is bounded planning
support. It does not automatically create a durable `Task`. A consultation
becomes a Task only when an independently governed deliverable is required.

## Specialist authority

### Data Explorer

Data Explorer has exclusive dataset access. It may inspect admitted datasets,
perform bounded data operations, and return observations, diagnostics,
artifacts, `AnalysisFrame` material, limitations, and blockers.

It cannot define or own a Hypothesis, evaluate a Hypothesis, create a
Discovery, perform governance, own durable Evidence admission, write directly
to persistence, or interact directly with the human.

### Hypothesis Analyst

Hypothesis Analyst is the scientific investigation controller. It owns
scientific feasibility; at most one Hypothesis for an eligible feasible leaf
`SCIENTIFIC` Task; the `InvestigationPlan`, `InvestigationProtocol`, Evidence
obligations, EvidenceRequest construction, governed protocol revision, and
protected final evaluation. Its final scientific act is a
`DiscoveryProposal` or a typed non-completion.

It cannot access datasets directly, bypass Data Explorer, persist
authoritatively, self-approve governance, or interact directly with the human.
Protected evaluation is part of this scientific authority; there is no
separate peer Evaluator agent.

### Graph Miner

Graph Miner is a read-only research-state inquiry specialist. It may return
object references, graph paths, contradictions, gaps, validity and dependency
information, and suggestions for related Objectives.

It cannot mutate semantic graph state, create Evidence or Discovery, perform
dataset operations, perform governance, admit cross-Objective relations, or
interact directly with the human.

## Governance authority

Governance may approve, reject, hold, request correction, request additional
Evidence, or request conflict review for an exact eligible proposal.

Governance does not edit a Hypothesis, protocol, evaluation, or
`DiscoveryProposal` into preferred wording. A correction request returns the
matter to the authority that owns the scientific content. That authority must
produce a revised proposal with a new traceable identity or version before
governance can consider it again.

Governance approval is authorization, not admission. Application authority
still validates the exact approved proposal and applies the durable transition.

## Application authority

Application authority owns identity allocation, typed validation, admission,
persistence, transaction boundaries, lifecycle transitions, plan activation,
Evidence admission, governance application, Discovery admission, validity
propagation, outbox and inbox state, leases, fencing, replay, idempotency,
restart safety, and fail-closed enforcement.

Its canonical rule is:

```text
agents propose or return bounded results
application authority validates and admits durable state
```

Application authority does not decide what the research means. It ensures that
only the designated authority can make each transition and that a failure does
not leave half-admitted state.

## Prohibited authority combinations

| Prohibited combination | Why it is unsafe |
| --- | --- |
| Planner plus scientific operationalization | planning intent could silently determine the test and its conclusion |
| Data Explorer plus protected evaluation | the observer could reinterpret its own output outside the admitted scientific contract |
| Hypothesis Analyst plus dataset access | scientific authority could bypass the bounded observation contract |
| any specialist plus governance | a proposal could approve itself |
| any agent plus authoritative persistence | model output could become durable state without typed admission |
| governance plus scientific rewriting | approval would become untraceable scientific authorship |
| Graph Miner plus mutation | inquiry and retrieved context could alter the state being inspected |
| presentation plus admission | a GeneratedView could be mistaken for Evidence or Discovery |

These are authority separations, not necessarily process boundaries. A single
application may host several roles, but their contracts, allowed inputs,
outputs, and transition permissions must remain distinct and auditable.

## Acts that must remain distinct

```text
proposal
!= approval
!= execution
!= observation
!= Evidence admission
!= protected evaluation
!= governance
!= Discovery admission
```

An execution output is not automatically Evidence. Admitted Evidence is not
automatically a Discovery. A protected evaluation is not governance. A
governance approval is not the durable write. Preserving these distinctions is
the core authority invariant.

See [Planner architecture](planner-architecture.md),
[Executor and dispatch](executor-and-dispatch.md), and
[Persistence and admission](persistence-and-admission.md) for the operational
contracts that enforce this taxonomy.
