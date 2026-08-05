# CogniEDA documentation

CogniEDA is **validity-preserving research-state infrastructure** for analytical investigation. It is designed to keep research intent, data state, assumptions, test contracts, observations, claims, validity, and active context distinct and traceable over time.

This documentation is for researchers evaluating the model, product and engineering contributors, architecture reviewers, and project owners. It starts with meaning and scientific boundaries; source-code knowledge is not required for the canonical reading journey.

## Documentation availability

The documentation set is being expanded. Entries marked **Planned** identify the intended owner page for a topic, but those paths are not yet available as canonical pages in the reading journey.

Markdown files elsewhere in the repository may describe earlier designs or current implementation details. They should not be treated as canonical unless linked from this index or explicitly identified as a stable reference.

Implementation-status claims must reflect the supported behavior of the current `main` branch and must distinguish present behavior from design targets.

## Recommended reading journey

Read the tracks in this order. Within each track, read from top to bottom.

### 1. Conceptual reading

| Reader question | Owner page | Availability |
| --- | --- | --- |
| What is CogniEDA, and what is it not? | [What is CogniEDA?](what-is-cognieda.md) | **Available** |
| Which analytical failures motivate it? | [Problem and thesis](problem-and-thesis.md) | **Available** |
| What is governed research state? | `concepts/research-state/` | **Planned** |
| How does a scientific investigation progress? | `concepts/scientific-lifecycle/` | **Planned** |
| How is validity preserved over time? | `concepts/validity/` | **Planned** |
| How are active context and continuity constructed? | `concepts/context/` | **Planned** |

Concept pages own meaning. They must explain epistemic roles and lifecycle consequences before describing implementation.

### 2. Architecture

| Architecture concern | Owner page | Availability |
| --- | --- | --- |
| System boundaries and major flows | `architecture/system-overview.md` | **Planned** |
| Human, agent, and application authority | `architecture/authority-boundaries.md` | **Planned** |
| Planner coordination and mutation proposals | `architecture/planner-architecture.md` | **Planned** |
| Specialist dispatch and execution boundaries | `architecture/executor-and-dispatch.md` | **Planned** |
| Persistence, admission, and transaction ownership | `architecture/persistence-and-admission.md` | **Planned** |
| End-to-end operational flow | `architecture/end-to-end-flow.md` | **Planned** |

Architecture pages may define implementation-neutral contracts and authority boundaries. They must not promote a current package layout into architectural meaning.

### 3. Reference

| Lookup need | Owner page | Availability |
| --- | --- | --- |
| FCO and non-FCO catalog | `reference/object-catalog.md` | **Planned** |
| Lifecycle states and scientific outcomes | `reference/lifecycle-and-outcome-catalog.md` | **Planned** |
| Contracts and cardinalities | `reference/contract-and-cardinality-reference.md` | **Planned** |
| Canonical terminology | `reference/terminology.md` | **Planned** |

Reference pages are concise lookup surfaces. They do not compete with concept pages for explanatory ownership.

### 4. Design decisions

Stable tradeoffs and owner decisions will be indexed at `design-decisions/index.md` when that page becomes available. Decision records explain why a boundary exists; they are not implementation logs. This track is **Planned**.

### 5. Current status

| Reader question | Owner page | Availability |
| --- | --- | --- |
| What is supported on current `main`? | `status/current-state.md` | **Planned** |
| What currently blocks or limits use? | `status/limitations-and-bottlenecks.md` | **Planned** |
| What improvements are being considered? | `status/future-improvements.md` | **Planned** |

Status pages describe reader-relevant capability boundaries. They must not become sprint plans, migration ledgers, temporary process histories, or package-by-package development histories.

## Status vocabulary

Reader-facing implementation claims use these terms:

- **Implemented** — supported behavior exists on the current `main` path and is backed by source evidence. The claim must name its boundary.
- **Verified on SQLite** — a qualifier for behavior exercised against SQLite; it is not a separate capability and does not imply another database is supported.
- **Partially implemented** — a coherent subset exists, but the complete reader- or user-facing capability does not.
- **Design target** — an established intended boundary that is not being described as current behavior.
- **Deferred** — work is intentionally postponed; no present capability is implied.
- **Known limitation** — a verified constraint of the current supported boundary.
- **Unsupported** — no supported current path exists, even if a seam or placeholder is present.

A schema alone does not imply a supported capability. A stub, fixture, catalog entry, configuration key, interface, or directory alone does not imply implementation. Design targets must never be described as current behavior.

## Public and local documentation boundary

Public documentation contains stable concepts, architecture, references, design decisions, and reader-relevant current status.

Local development material includes audits, prompts, recovery inventories, migration ledgers, temporary development reports, review packs, verification reports, source-level change planning, and pull-request process. It belongs under `.local/development/`, is excluded from the canonical reader journey, and is not linked from public pages.
