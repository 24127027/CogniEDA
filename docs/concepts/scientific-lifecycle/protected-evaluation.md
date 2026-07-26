# Protected evaluation

CogniEDA uses different inputs for deciding what to investigate and for deciding
what admitted Evidence justifies. Planning benefits from hypotheses, priorities,
provisional beliefs, and prior work. Scientific evaluation must be narrower.

This is context type safety:

> Relevance does not grant scientific authority.

The protected conclusion boundary exists so an Assumption, prior Discovery,
SessionFrame summary, user pin, or persuasive conversation cannot become an
inference premise merely by entering the same prompt.

> **Implementation status:** Repository-built protected evaluation is
> **Implemented**. The closed bundle, no-tool Analyst dependency, digest
> binding, and current separation from SessionFrame projections are enforced by
> schemas, application validation, and focused architecture tests. A default
> production Analyst model adapter is **Unsupported**.

## Planning Context and Protected Conclusion Context answer different questions

| Context | Question it answers | Typical authority |
| --- | --- | --- |
| Planning Context | What should the project investigate or do next? | research intent, workflow state, provisional beliefs, relevant prior knowledge, user priorities |
| Protected Conclusion Context | What bounded claim does this exact active Evidence justify for this exact Hypothesis? | approved test contract, accepted data identity, admitted observation, validated provenance, decision rule |

Planning Context may contain:

- the active `Objective`;
- proposed, active, or paused Tasks;
- accepted DataProfile information;
- active Assumptions;
- relevant prior Discoveries;
- selected Evidence summaries;
- user priorities and decisions;
- SessionFrame selections, pins, exclusions, warnings, and handoff state.

Those inputs are valuable because planning is exploratory. A prior Discovery can
motivate a new Task. An Assumption can reveal a prerequisite that should be
tested. A user can prefer one branch of work over another.

The tempting simpler design is to reuse that same context for evaluation.
Everything is already assembled and relevant. It is unsafe because planning
state mixes motivation with observation. A model can easily treat “we expect
response time to matter” as support for the response-time Hypothesis or reuse a
prior Discovery as if it were fresh Evidence.

The current decision is to reconstruct a separate, closed protected bundle from
durable authority. The tradeoff is duplicated context-building infrastructure
and less prompt flexibility. The protected boundary should be revisited only
when a proposed input category has a clear epistemic role, lifecycle rule, and
binding to the evaluated claim.

## What the protected bundle carries

The current protected input is the immutable
`DiscoverySynthesisBundle`. It is not a generic context bag. Each category
serves a specific epistemic purpose.

### Canonical Hypothesis

The Hypothesis is the evaluand. It supplies the exact statement, variables,
scope, method, parameters, decision rule, deterministic seed when applicable,
and Evidence expectation. The Analyst may interpret the Evidence against this
contract; it may not replace the contract with a more convenient one.

### Safe DataProfile metadata

The bundle identifies the active DataProfile accepted as ground truth and
includes its version fingerprint, source type, selected version labels, and
basic shape. It deliberately omits the filesystem dataset locator. This binds
the claim to one data state without granting the Analyst raw-data access.

### AnalysisFrame provenance

AnalysisFrame snapshots identify the exact admitted data view: its durable
identity, fingerprint, frame reference or hash, column references, and row
filter description. Their purpose is to preserve the scope of observation, not
to supply a narrative summary.

### ExecutionRun provenance

ExecutionRun snapshots bind the Evidence to the fenced admitted attempt, direct
Task and Hypothesis, AnalysisFrame, executor and method identities, parameter
hash, attempt version, and run fingerprint. They show which execution produced
the observation without making execution status a scientific outcome.

### Complete active admitted Evidence

The bundle includes the exact active Evidence set for the Hypothesis. Each
snapshot carries immutable observed-result content, method and parameters,
limitations, selected code/environment references, and an Evidence
fingerprint. Superseded, invalidated, or non-admitted observations are not
substituted because they sound relevant.

### Method, decision rule, limitations, and invalidators

The approved method and parameters define how the claim was tested. The
decision rule defines what outcomes the contract permits. Evidence limitations
must survive into any proposal, and required invalidators state which later
changes would remove active authority.

These values prevent the Analyst from silently changing the test after seeing
the result.

### Lineage manifest and deterministic digests

The bundle has a deterministic input digest. A closed provenance manifest
records the authoritative repository source, object identity, fingerprint,
inclusion role, and active-state proof for each Hypothesis, DataProfile,
AnalysisFrame, ExecutionRun, and Evidence item.

The digest is not scientific proof. It is a binding mechanism: exact retry can
identify the same input, while changed data, Evidence, provenance, contract, or
ordering becomes a different evaluation. Evaluation keys, Evidence-set
digests, proposal digests, decisions, and admission plans carry that identity
forward.

## What the protected boundary excludes

Protected Conclusion Context has no field for:

- Assumptions;
- Tasks, Task motivation, or Planner operations;
- prior Discoveries;
- SessionFrames;
- raw chat or message history;
- arbitrary context dictionaries or user-provided prompt bags;
- raw datasets, dataset locators, or files;
- user pins or exclusions as scientific authority;
- retrieval ranks, relevance scores, or candidate lists;
- governance authority or decisions;
- cache entries or tool-result caches;
- GeneratedViews or generated summaries;
- repositories, SQL sessions, or application services.

The exclusion is structural. Unknown bundle fields fail schema validation. The
Analyst dependency object contains only the bundle, the agent has no tools, and
the runner supplies no message history. A prompt instruction to “ignore
Assumptions” would be weaker because the unsafe content would still be visible.

This decision protects against both accidental influence and authority
laundering. Its cost is that the Analyst cannot look up a missing detail on
demand. Missing or inadequate authoritative input must produce a typed
`EvaluationFailure`, not an improvised answer.

## Assumption quarantine

An Assumption may guide planning, decomposition, and the decision to open a
Task. It is intentionally absent from evaluation even when it concerns the
same variables or cohort.

In the running example, “trial accounts are already excluded” may be useful
planning state. It cannot support the churn conclusion. The approved
AnalysisFrame and Evidence must establish which accounts were actually
included.

After a Discovery is admitted, another process may compare it with Assumptions
and flag a contradiction for review. That comparison occurs after the
scientific claim exists. It does not retroactively make the Assumption an
inference premise or automatically rewrite either object.

The tempting alternative is to retain Assumptions with confidence labels and
ask the model to discount them. That still exposes the proposed conclusion to
unobserved premises. Structural absence is the current decision. The tradeoff
is that relevant planning context must sometimes be converted into a testable
Task before it can influence a claim.

## Repository-built authority

The protected path does not trust a caller-supplied bundle. The application
starts from a Hypothesis identity and reloads authoritative state:

```text
Hypothesis identity
  -> active terminal analytical Task and approved specification
  -> active accepted DataProfile
  -> complete active Evidence set
  -> admitted AnalysisFrame and ExecutionRun lineage
  -> canonical snapshots and manifest
  -> deterministic DiscoverySynthesisBundle
```

Construction fails closed when:

- the Hypothesis is not ready for evaluation;
- the source Task is not active, analytical, and terminal;
- the approved Task and Hypothesis contracts disagree;
- the DataProfile is not active and accepted as ground truth;
- no active admitted Evidence exists;
- Evidence, AnalysisFrame, ExecutionRun, outbox, method, parameters, or
  DataProfile lineage disagrees;
- a current Discovery already exists for the Hypothesis;
- the contract version is unsupported.

Governance and Discovery admission reconstruct the bundle again, with narrowly
controlled allowance for the already evaluated/committed replay path. They do
not rely on the earlier model invocation's in-memory object.

This repeated reconstruction costs repository reads and validation work. It
protects changed-binding detection and prevents stale detached state from
becoming persistence authority.

## The generic SessionFrame projection is not protected evaluation

`SessionContextBuilder` under `src/memory/` can construct a `ContextBundle` with
mode names such as conclusion or Discovery synthesis. That projection is
derived from SessionFrame summaries. It excludes several unsafe categories,
but it remains generic active-context infrastructure:

- it contains summaries rather than the complete canonical snapshots;
- it is selected from a SessionFrame rather than rebuilt from authoritative
  evaluation repositories;
- it does not carry complete AnalysisFrame and ExecutionRun lineage;
- it does not prove the exact active Evidence set or approved outbox contract;
- its objective snapshot and warnings are useful context, not scientific
  premises;
- it is not the Analyst dependency type.

No supported production call site passes that projection to protected
evaluation. Planner call sites request Planning Context. The evaluation runner,
governance verification, and Discovery admission use
`build_synthesis_bundle` instead. An architecture test prevents the protected
Analyst, evaluation, governance, and Discovery packages from consuming
`SessionContextBuilder` or `ContextBundle`.

The similar mode name remains a maintenance hazard because a future contributor
could mistake policy-filtered summaries for scientific authority. Renaming or
refactoring that helper is outside the current documentation boundary. The
enforced rule is simpler: SessionFrame-derived context must never be substituted
for the repository-built protected bundle.

## Tool isolation protects authority, not just security

Removing tools from the Analyst does more than reduce attack surface. A database
query, file read, retrieval call, or governance lookup would let the Analyst
expand its own scientific premises beyond the reviewed bundle.

The tempting alternative is to give the Analyst read-only tools and trust it to
cite what it used. That makes the effective input depend on model behavior,
tool timing, and mutable external state. A later reviewer could not reconstruct
the proposal from the bundle digest alone.

The current tool-free boundary keeps every scientific input explicit and
deterministic. The cost is that evaluation stops when required information is
missing. A future tool capability should be considered only if its output can
be admitted into a new typed, immutable, digest-bound bundle before scientific
evaluation begins.

## Failures are not scientific outcomes

The four epistemic outcomes—supported, contradicted, inconclusive, and
insufficient evidence—are valid proposal statuses when the bundle supports a
bounded interpretation.

`EvaluationFailure` is different. It records that the protected evaluation
could not produce a valid proposal, for example because lineage is invalid,
mandatory provenance is missing, evaluation is not identifiable, the contract
version is unsupported, the provider failed, or structured output remained
invalid after bounded retries.

Application code must persist or route the typed failure. It must not turn
“evaluation could not be completed” into “the result is inconclusive,” because
that would manufacture a scientific outcome from a technical or contract
failure.

## Design costs and revisit triggers

| Mechanism | Invariant protected | Tradeoff | Revisit trigger |
| --- | --- | --- | --- |
| separate planning and conclusion contexts | motivation cannot become observation | parallel context infrastructure | a unified type system can still prevent cross-role use |
| closed typed bundle | only reviewed input categories reach evaluation | schema evolution requires explicit versions | a new authoritative input category is needed |
| Assumption quarantine | provisional belief cannot support a claim | planning beliefs must be tested separately | never without a change to the project thesis |
| repository reconstruction | current durable state is the authority | repeated reads and validation | another source can provide equivalent immutable snapshots |
| no Analyst tools or history | effective scientific input is deterministic | missing details cause failure | tool output can be admitted before evaluation |
| digests and manifests | exact input and lineage can be rebound later | more persisted coordination metadata | a stronger portable identity mechanism replaces them |

## Current limitations

- The protected evaluation service is an in-process library path. A production
  worker and default Analyst provider are **Unsupported**.
- Safe DataProfile metadata and selected code/environment references are not a
  complete reproducibility envelope.
- The generic mode-named SessionFrame projection remains in `src/memory/`; its
  separation is enforced, but its naming can still confuse readers of the
  source.
- Cross-database transaction behavior is **Unsupported**. Current race and
  binding behavior is **Verified on SQLite**.
- SessionFrame reconstruction, active retrieval policy, user pin/exclusion
  semantics, and continuity are owned by
  [SessionFrame and active context](../context/session-frame.md),
  [Context type safety and retrieval](../context/context-type-safety.md),
  and [Context continuity and resume](../context/continuity-and-resume.md).

## Related decision rationale

The broader tradeoff between useful planning context and admissible scientific
premises is summarized in
[Design decisions and tradeoffs](../../design-decisions/index.md).
[Assumptions guide planning only](../../design-decisions/assumptions-guide-planning-only.md) records the Assumption
quarantine decision, and
[Scientific authority by role](../../design-decisions/scientific-authority-by-role.md) records the
closed specialist-authority boundary.

## Implementation orientation

The closed contracts are under `src/schemas/evaluation/`. Repository
reconstruction and durable evaluation control are under
`src/application/evaluation/`. The no-tool specialist boundary is under
`src/agents/executor/hypothesis_analyst/`.

Focused verification is under `tests/application/evaluation/`,
`tests/agents/`, and `tests/architecture/`.

Return to [Scientific authority](scientific-authority.md), or continue to
[Discovery governance and admission](discovery-governance-and-admission.md).
