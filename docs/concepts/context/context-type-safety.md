# Context type safety

Context type safety ensures that every selected record has the epistemic type,
authority, lifecycle, scope, lineage, validity, freshness, and permitted use
required by the current reasoning mode. Relevance is considered only after
those structural obligations pass.

This page defines the **target design** for mode-specific eligibility and
exclusion. The named record types do not freeze a wire schema.

## Eligibility dimensions

Context selection must consider:

- epistemic type;
- authoring, governance, and admission authority;
- lifecycle;
- Objective scope;
- DataProfile scope;
- scientific lineage and contract revision;
- validity and invalidators;
- current reasoning mode;
- permitted use;
- freshness;
- explicit exclusion rules.

Failure to establish a required dimension excludes the candidate. A model may
not infer missing authority or lineage from prose.

## Mode-specific eligibility

| Mode | May include | Must preserve or exclude |
| --- | --- | --- |
| planning | Objective; approved or proposed PlanRevision state; Tasks; active Assumptions; DataProfiles; valid Discoveries for planning reference; Graph Miner findings; Data Explorer consultation results; limitations and blockers | planning materials remain non-scientific; wrong-Objective or invalid state is excluded or clearly bounded for authorized review |
| planning consultation | exact consultation request, admitted DataProfile references where applicable, eligible planning context, limitations, blockers | consultation is bounded; output is not automatically a Task, Evidence, or Discovery |
| scientific investigation control | eligible leaf SCIENTIFIC Task; ScientificInvestigationRun; Hypothesis; active protocol revision; Evidence obligations and requests; admitted Evidence and provenance needed to decide next scientific action | Planner and Assumption content cannot operationalize science; Hypothesis Analyst receives no dataset access |
| protected evaluation | exact Hypothesis; admitted DataProfile; active protocol revision; Evidence obligations; AnalysisFrame provenance; admitted eligible Evidence; method, parameters, decision rule, uncertainty, limitations, claim scope, validity basis, necessary provenance | closed bundle only; all protected exclusions below apply |
| Graph Miner inquiry | Objective-scoped eligible object references, typed relationships, validity state, gaps, conflicts, dependencies, traversal bounds | read-only; no mutation, dataset work, Evidence/Discovery creation, or cross-Objective relation admission |
| user-facing answer or GeneratedView | eligible existing state, normalized outcomes, limitations, blockers, source references, validity warnings | summary remains presentation; it does not become Evidence or Discovery |
| recovery and resume | durable identity, lifecycle, lineage, approval, validity, operational ownership, pending work, and permitted-next-action records | prose may explain but never establish authority |
| validity review | affected historical records, typed dependencies, validity events, authorization, review obligations, restrictions, and restoration state | historical visibility does not authorize protected reuse |

## Protected evaluation exclusions

Protected evaluation must exclude:

- Assumptions;
- prior Discoveries as inference premises;
- raw conversation;
- failed reasoning;
- unrelated Objectives;
- unverified GeneratedViews;
- invalid, superseded, stale, or wrong-scope Evidence;
- fuzzy cross-Objective matches;
- unsupported summaries;
- rejected Tasks and other workflow state that cannot serve as scientific
  support;
- cache entries or retrieval scores treated as authority.

These are structural exclusions. Prompt wording, model judgment, relevance
score, user convenience, or prior inclusion in a SessionFrame cannot override
them.

## Planning is broader, not ungoverned

Planning context may use active Assumptions, valid Discoveries, consultation
findings, limitations, and blockers because planning decides what work to
consider. Those records retain their original roles. A Discovery may motivate
new work; an Assumption may constrain a plan; neither becomes Evidence for a
new claim.

A Discovery-Assumption contradiction may create a planning review signal. The
signal does not rewrite either object, promote the Assumption to Evidence, or
constitute a scientific conclusion.

## User-facing answer context

Answer context may summarize eligible admitted state for the user. It may cite
an existing valid Discovery or describe historical state with explicit
validity warnings. The resulting answer or GeneratedView remains derived
presentation.

If the requested answer would assert a new scientific claim, answer context is
not a shortcut. The claim must follow scientific operationalization, Evidence
admission, protected evaluation, governance, and Discovery admission.

## Fail-closed construction

When required identity, scope, authority, lineage, lifecycle, or validity
cannot be proven, construction returns an exclusion, blocker, or review
requirement. It does not insert a candidate provisionally and ask downstream
reasoning to sort it out.

The protected EvaluationBundle is distinct from SessionFrame. Application
authority constructs or validates the closed bundle for one investigation and
protocol revision; a raw frame or retrieval result cannot substitute for it.

## Implementation status

**Partially implemented.** Current `SessionContextBuilder` projects planning,
answer, conclusion, and discovery-synthesis bundles. The protected synthesis
projection excludes Assumptions, Tasks, prior Discoveries, user decisions,
pending questions, stale context, dead ends, and cached tool summaries, and it
filters profile and Evidence lifecycle. A separate pure retrieval policy
rejects unknown types and unsafe lifecycle/mode combinations.

The current mode vocabulary does not cover planning consultation, scientific
investigation control, Graph Miner inquiry, recovery, or validity review as
first-class modes. Objective identity and full scientific lineage are not
bound by the current SessionFrame projection, and current conclusion handling
is a legacy alias for discovery synthesis rather than the canonical
EvaluationBundle.
