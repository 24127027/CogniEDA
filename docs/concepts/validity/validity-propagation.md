# Validity propagation

Validity propagation determines how an explicit change in one admitted record
affects downstream eligibility. It follows typed dependency and authority
contracts; it is not an arbitrary traversal over every reachable node.

This page defines the **target design**. Exact propagation-event schemas and
storage mechanisms remain unfrozen.

## Typed dependency path

Potential propagation paths include:

```text
DataProfile
  -> ExecutionRun / AnalysisFrame
  -> Evidence
  -> EvaluationBundle
  -> DiscoveryProposal
  -> Discovery
  -> SessionFrame / GeneratedView eligibility
```

The sequence includes FCOs, provenance, evaluation state, proposals, active
context, and presentation. It does not promote the non-FCO records into the
semantic Knowledge Graph. Nor does it imply that every upstream event reaches
every downstream record.

## Propagation decision

For each candidate dependency, application authority must evaluate:

1. the exact relationship type;
2. the contract or obligation affected by the event;
3. Objective, DataProfile, population, cohort, and claim scope;
4. the lifecycle state of both records;
5. the validity-event class;
6. the current use being requested;
7. protected-evaluation admission and exclusion rules.

Only an admitted typed relationship can carry a validity consequence. Textual
similarity, graph proximity, a shared keyword, or appearance in one
SessionFrame is insufficient.

## Representative propagation consequences

| Upstream change | Typed dependency check | Potential downstream consequence |
| --- | --- | --- |
| DataProfile superseded | exact DataProfile binding in AnalysisFrame, Evidence, or validity basis | Evidence becomes historical or ineligible for a protected use; dependent Discovery requires review |
| measurement semantics changed | exact variable and measurement contract | affected Evidence, EvaluationBundle, proposal, and claim eligibility require review |
| protocol revised | exact protocol revision and Evidence obligation | earlier Evidence remains historical but may be excluded from the new EvaluationBundle |
| Evidence invalidated | exact Discovery Evidence reference | exclude from protected evaluation; flag, restrict, or invalidate dependent proposal or Discovery under policy |
| provenance defect | exact attempt, frame, artifact, digest, code, or environment binding | exclude every use whose authority depends on the defective binding |
| scope restriction | exact population, cohort, Objective, or claim-scope relation | allow only the proven narrower use; fail closed elsewhere |

These are conceptual outcomes, not a universal state-transition table. The
authorized validity policy determines the exact transition for each typed
case.

## Protected evaluation

Invalid, superseded, wrong-scope, stale, or otherwise ineligible Evidence must
not silently enter an EvaluationBundle. Eligibility is checked against the
exact ScientificInvestigationRun, active protocol revision, Evidence
obligation, DataProfile, AnalysisFrame, provenance, and current use.

An earlier EvaluationBundle is a historical account of the evaluation that
occurred. If an input later loses eligibility, that bundle is not silently
rewritten; it is no longer reusable for an affected protected evaluation. A
new evaluation requires a newly closed eligible bundle.

DiscoveryProposal and governance state receive the same protection. A pending
proposal whose supporting lineage becomes ineligible cannot proceed merely
because it was already generated or approved. Application authority must
recheck current eligibility at Discovery admission.

## Discovery review

A validity change in supporting Evidence can trigger review of a dependent
Discovery. Review is not automatic scientific rewriting. Depending on the
typed event and authorized policy, the Discovery may remain active with a
warning for some uses, become restricted, be flagged, be invalidated, or be
superseded through new scientific lineage.

Historical inspection remains possible for authorized users. Presentation
must distinguish the original claim and admission from its current eligibility.

## SessionFrame and GeneratedView eligibility

A SessionFrame selects governed references for a purpose. When a selected
source loses eligibility, the frame must be reviewed, superseded, or
reconstructed for the affected use. The selected object's own validity and
authority do not come from frame membership.

A GeneratedView is derived presentation. It may be regenerated from currently
eligible sources or marked stale and withheld. It is never corrected as if it
were authoritative Evidence or Discovery, and it cannot restore validity to a
source.

## Downstream review and restoration

Propagation should produce explicit review obligations when a downstream
decision cannot be made mechanically from the typed contract. Review must
retain the triggering event, affected relationship, scope, current use, and
permitted next actions.

An upstream restoration does not blindly clear every downstream restriction.
Each affected dependency is reconsidered under its own contract and current
use. Eligibility is restored only where exact authorization and obligations
are satisfied.

## Cross-Objective boundary

Propagation remains Objective-scoped. It does not search for semantically
similar records in other Objectives and does not create cross-Objective
relations. Cross-Objective Evidence reuse requires explicit admission and
exact equality over the relevant versioned canonical typed obligations; any
unproven equality fails closed.

## Implementation status

**Partially implemented.** At narrow repository boundaries, current source can
propagate DataProfile supersession to directly scoped Evidence and Discovery
review state when repositories are supplied in the same database session. It
can also propagate Evidence supersession or invalidation to directly dependent
Discovery review flags. Retrieval policy excludes invalidated or superseded
Evidence from protected synthesis modes and excludes flagged or invalidated
Discoveries from answer context.

The complete typed path through ExecutionRun, AnalysisFrame,
EvaluationBundle, DiscoveryProposal, SessionFrame reconstruction, and
GeneratedView staleness is not implemented end to end. Existing optional
repository calls must not be described as a general propagation service.
