# CogniEDA documentation

CogniEDA is **validity-preserving research-state infrastructure** for analytical investigation. It is designed to keep research intent, data state, assumptions, test contracts, observations, claims, validity, and active context distinct and traceable over time.

This documentation is for researchers evaluating the model, product and engineering contributors, architecture reviewers, and project owners. It starts with meaning and scientific boundaries; source-code knowledge is not required for the canonical reading journey.

## Documentation availability

All canonical tracks listed below are **Available**. Markdown files elsewhere
in the repository may be supporting material, package instructions, or
internal development guidance. They do not compete with the owner pages linked
here.

Implementation-status claims must distinguish supported behavior from design
targets.

## Recommended reading journey

Read the tracks in this order. Within each track, read from top to bottom.

### 1. Foundation

| Reader question | Owner page | Availability |
| --- | --- | --- |
| What is CogniEDA, and what is it not? | [What is CogniEDA?](what-is-cognieda.md) | **Available** |
| Which analytical failures motivate it? | [Problem and thesis](problem-and-thesis.md) | **Available** |
| What is governed research state? | [Research-state foundation](concepts/research-state/index.md) | **Available** |
| How are objects classified across state layers? | [Objects and state layers](concepts/research-state/objects-and-state-layers.md) | **Available** |
| How are planning and scientific state kept separate? | [Planning and scientific state](concepts/research-state/planning-and-scientific-state.md) | **Available** |
| How do identity, scope, and lineage constrain reuse? | [Identity, scope, and lineage](concepts/research-state/identity-scope-and-lineage.md) | **Available** |

Concept pages own meaning. They must explain epistemic roles and lifecycle consequences before describing implementation.

### 2. Architecture

| Architecture concern | Owner page | Availability |
| --- | --- | --- |
| System boundaries and major flows | [System overview](architecture/system-overview.md) | **Available** |
| Canonical architecture versus the executable MVP | [MVP runtime subset](architecture/mvp-runtime-subset.md) | **Available** |
| Human, agent, and application authority | [Authority boundaries](architecture/authority-boundaries.md) | **Available** |
| Planner coordination and mutation proposals | [Planner architecture](architecture/planner-architecture.md) | **Available** |
| Specialist dispatch and execution boundaries | [Executor and dispatch](architecture/executor-and-dispatch.md) | **Available** |
| Persistence, admission, and transaction ownership | [Persistence and admission](architecture/persistence-and-admission.md) | **Available** |
| End-to-end operational flow | [End-to-end flow](architecture/end-to-end-flow.md) | **Available** |
| Current Python package ownership | [Source layout](development/source-layout.md) | **Available** |

Architecture pages may define implementation-neutral contracts and authority boundaries. They must not promote a current package layout into architectural meaning.

### 3. Scientific lifecycle

| Reader question | Owner page | Availability |
| --- | --- | --- |
| How does a scientific investigation progress? | [Scientific lifecycle](concepts/scientific-lifecycle/index.md) | **Available** |
| Who owns scientific feasibility and operationalization? | [Scientific authority](concepts/scientific-lifecycle/scientific-authority.md) | **Available** |
| How do observations become Evidence? | [Evidence and AnalysisFrames](concepts/scientific-lifecycle/evidence-and-analysis-frames.md) | **Available** |
| What may enter protected evaluation? | [Protected evaluation](concepts/scientific-lifecycle/protected-evaluation.md) | **Available** |
| How are proposals governed and Discoveries admitted? | [Discovery governance](concepts/scientific-lifecycle/discovery-governance.md) | **Available** |

### 4. Validity

| Reader question | Owner page | Availability |
| --- | --- | --- |
| How is historical truth separated from current-use eligibility? | [Validity](concepts/validity/index.md) | **Available** |
| How do validity states change over time? | [Validity over time](concepts/validity/validity-over-time.md) | **Available** |
| How do typed validity consequences propagate? | [Validity propagation](concepts/validity/validity-propagation.md) | **Available** |

### 5. Context and continuity

| Reader question | Owner page | Availability |
| --- | --- | --- |
| How is active context constructed? | [Context](concepts/context/index.md) | **Available** |
| What does SessionFrame govern? | [SessionFrame](concepts/context/session-frame.md) | **Available** |
| Which records are eligible for each reasoning mode? | [Context type safety](concepts/context/context-type-safety.md) | **Available** |
| Why must eligibility precede relevance? | [Retrieval strategy](concepts/context/retrieval-strategy.md) | **Available** |
| How is governed state resumed across sessions? | [Continuity and resume](concepts/context/continuity-and-resume.md) | **Available** |

### 6. Reference

| Lookup need | Owner page | Availability |
| --- | --- | --- |
| FCO and non-FCO catalog | [Object catalog](reference/object-catalog.md) | **Available** |
| Lifecycle states and scientific outcomes | [Lifecycle and outcome catalog](reference/lifecycle-and-outcome-catalog.md) | **Available** |
| Contracts and cardinalities | [Contract and cardinality reference](reference/contract-and-cardinality-reference.md) | **Available** |
| Canonical terminology | [Terminology](reference/terminology.md) | **Available** |

Reference pages are concise lookup surfaces. They do not compete with concept pages for explanatory ownership.

### 7. Design decisions

| Reader question | Owner page | Availability |
| --- | --- | --- |
| Which architecture decisions and tradeoffs are stable? | [Design decisions](design-decisions/index.md) | **Available** |

Decision records explain why a boundary exists; they are not implementation
logs or proof of current support.

### 8. Current status

| Reader question | Owner page | Availability |
| --- | --- | --- |
| What is currently supported? | [Current state](status/current-state.md) | **Available** |
| What currently blocks or limits use? | [Limitations and bottlenecks](status/limitations-and-bottlenecks.md) | **Available** |
| What improvements are established, deferred, exploratory, or unresolved? | [Future improvements](status/future-improvements.md) | **Available** |

Status pages describe reader-relevant capability boundaries rather than
implementation chronology.

## Status vocabulary

Reader-facing implementation claims use these terms:

- **Implemented** — supported behavior exists and is backed by source evidence.
  The claim must name its boundary.
- **Verified on SQLite** — a qualifier for behavior exercised against SQLite; it is not a separate capability and does not imply another database is supported.
- **Partially implemented** — a coherent subset exists, but the complete reader- or user-facing capability does not.
- **Design target** — an established intended boundary that is not being described as current behavior.
- **Deferred** — work is intentionally postponed; no present capability is implied.
- **Known limitation** — a verified constraint of the current supported boundary.
- **Unsupported** — no supported current path exists, even if a seam or placeholder is present.

A schema alone does not imply a supported capability. A stub, fixture, catalog
entry, configuration key, interface, or directory alone does not imply
implementation. Design targets must never be described as current behavior.
