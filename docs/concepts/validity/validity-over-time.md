# Validity over time

Scientific and operational state must remain truthful about the past while
protecting current use. CogniEDA therefore records validity changes as explicit
events and relations instead of editing old scientific payloads to look as if
the new understanding had always existed.

This page defines the **target design** for truth-to-record and validity events.
It does not prescribe exact event fields, tables, or serialization.

## Historical truth and current authority

Historical truth-to-record answers what an authorized record said, observed,
or decided at a particular time. Current authority answers whether that record
is eligible for a specified use now.

| Example | Historical truth-to-record | Current-use posture |
| --- | --- | --- |
| an Evidence observation used DataProfile version A | the observation and its admitted lineage remain recorded | it may be excluded from a new protected evaluation after version A is superseded |
| a Discovery was admitted from then-eligible Evidence | the admission and exact claim remain recorded | it may be flagged, restricted, invalidated, or superseded for current presentation |
| a GeneratedView summarized eligible state | the view and its sources may remain auditable | it may be stale and require regeneration |

Immutability does not mean permanent current validity. It means the admitted
payload is not silently rewritten when its eligibility changes.

## Explicit validity events

A validity change must be explicit, durable, attributable, and traceable. A
validity event conceptually identifies the affected state, the authorized act,
the reason, relevant scope, lineage or contract, time, and resulting review or
eligibility consequence. Exact fields remain unfrozen.

The model must be able to represent at least these event classes:

| Event class | Meaning | Required posture |
| --- | --- | --- |
| invalidation | the state cannot support one or more current uses | preserve the record; exclude affected protected uses |
| supersession | a traceable successor replaces the prior state for a governed use | retain both identities and the successor relation |
| correction | prior content or execution was wrong and replacement work is required | create new scientific state; do not edit admitted payload |
| changed DataProfile | the admitted data state has changed | create a new immutable DataProfile and review typed dependents |
| changed measurement semantics | the meaning or unit of a measured variable changed | review every contract and dependent use that relied on that meaning |
| changed protocol | the active scientific procedure changed | preserve a protocol revision and re-evaluate Evidence eligibility |
| changed population or cohort | the governed population scope changed | prevent unsupported carry-over outside exact admitted scope |
| provenance defect | a required source, attempt, artifact, digest, or environment binding is defective | exclude state whose authority depends on that provenance |
| conflict | eligible state is in tension with another admitted record | create review state; do not silently choose or rewrite a side |
| scope restriction | use remains permitted only within a narrower scope | enforce the restriction at selection and presentation |
| restored validity | a previously restricted use is explicitly reauthorized | record the authorization and exact restored use; never infer restoration |

An event can affect different uses differently. A superseded Evidence record
may remain available for an authorized historical audit while being excluded
from a new EvaluationBundle. The validity model must therefore retain purpose
and scope rather than collapsing everything into one timeless flag.

## Invalidation, supersession, and correction

These acts are related but not interchangeable:

- **Invalidation** removes eligibility for an affected use without requiring a
  replacement.
- **Supersession** names a successor that replaces the prior record for a
  governed use.
- **Correction** performs new work or creates new scientific content because
  the prior content was wrong or defective.

Correction of analytical output creates new Evidence and an explicit relation
to the prior Evidence. If the correction changes the resulting claim, the
applicable scientific, governance, and admission path must run again. Neither
Evidence nor Discovery content is manually patched in place.

## Scope changes

Validity is always scoped. Changes to DataProfile identity, measurement
semantics, method, protocol, population, cohort, limitation contract, or claim
scope may invalidate one use while leaving a narrower historical statement
accurate.

Scope containment or compatibility must not be inferred from prose or
similarity. If the versioned typed obligations needed to establish eligibility
cannot be proven, the current use fails closed.

## Conflict and Assumption review

An Assumption is planning-only. After a Discovery is admitted, a
Discovery-Assumption contradiction may create a review signal. That signal
must not:

- rewrite the Assumption automatically;
- rewrite the Discovery automatically;
- promote the Assumption to Evidence;
- become a scientific conclusion by itself.

The review may lead to retained, replaced, or otherwise lifecycle-governed
planning state, or to new scientific work. The contradiction marker itself is
not scientific support.

## Restoration

Validity is restored only through an explicit authorized act that identifies
the exact state, scope, purpose, and basis being restored. Disappearance of a
warning, a newer timestamp, successful retrieval, or model confidence cannot
restore validity.

Restoration does not erase the invalidation interval or its reason. Downstream
objects that were restricted or marked stale require their own typed review;
they do not all become eligible automatically.

## Implementation status

**Partially implemented.** Current repositories can supersede a DataProfile,
mark directly scoped Evidence as historical, flag directly dependent
Discoveries, supersede or invalidate Evidence without changing its observed
payload, and flag dependent Discoveries for review. Assumption contradiction
flagging preserves the Assumption statement.

These are narrow repository transitions, not the complete target validity-
event and authorization model. Current enums and lifecycle metadata do not
constitute a frozen general event schema or an explicit restoration workflow.
