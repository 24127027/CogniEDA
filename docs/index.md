# CogniEDA documentation

CogniEDA is **validity-preserving research-state infrastructure** for analytical investigation. It is designed to keep research intent, data state, assumptions, test contracts, observations, claims, validity, and active context distinct and traceable over time.

This documentation is for researchers evaluating the model, product and engineering contributors, architecture reviewers, and project owners. It starts with meaning and scientific boundaries; source-code knowledge is not required for the canonical reading journey.

## Documentation recovery status

This index establishes the reader-first information architecture in review unit D0–D1. Most destination pages below are deliberately marked **Planned** because their architecture content must be reconciled in later human-reviewed units. A tracked Markdown file is not canonical merely because it already exists.

Implementation-status claims in reader-facing documentation must be verified against the current `main` branch. Documentation from other branches may be used as an information-architecture donor, but its implementation claims do not transfer without independent verification.

## Recommended reading journey

Read the tracks in this order. Within each track, read from top to bottom.

### 1. Conceptual reading

| Reader question | Owner page | Availability |
| --- | --- | --- |
| What is CogniEDA, and what is it not? | `what-is-cognieda.md` | **Planned — D2 or later** |
| Which analytical failures motivate it? | `problem-and-thesis.md` | **Planned — D2 or later** |
| What is governed research state? | `concepts/research-state/` | **Planned — D2 or later** |
| How does a scientific investigation progress? | `concepts/scientific-lifecycle/` | **Planned — later review unit** |
| How is validity preserved over time? | `concepts/validity/` | **Planned — later review unit** |
| How are active context and continuity constructed? | `concepts/context/` | **Planned — later review unit** |

Concept pages own meaning. They must explain epistemic roles and lifecycle consequences before describing implementation.

### 2. Architecture

| Architecture concern | Owner page | Availability |
| --- | --- | --- |
| System boundaries and major flows | `architecture/system-overview.md` | **Planned — later review unit** |
| Human, agent, and application authority | `architecture/authority-boundaries.md` | **Planned — later review unit** |
| Planner coordination and mutation proposals | `architecture/planner-architecture.md` | **Planned — later review unit** |
| Specialist dispatch and execution boundaries | `architecture/executor-and-dispatch.md` | **Planned — later review unit** |
| Persistence, admission, and transaction ownership | `architecture/persistence-and-admission.md` | **Planned — later review unit** |
| End-to-end operational flow | `architecture/end-to-end-flow.md` | **Planned — later review unit** |

Architecture pages may define implementation-neutral contracts and authority boundaries. They must not promote a current package layout into architectural meaning.

### 3. Reference

| Lookup need | Owner page | Availability |
| --- | --- | --- |
| FCO and non-FCO catalog | `reference/object-catalog.md` | **Planned — later review unit** |
| Lifecycle states and scientific outcomes | `reference/lifecycle-and-outcome-catalog.md` | **Planned — later review unit** |
| Contracts and cardinalities | `reference/contract-and-cardinality-reference.md` | **Planned — later review unit** |
| Canonical terminology | `reference/terminology.md` | **Planned — later review unit** |

Reference pages are concise lookup surfaces. They do not compete with concept pages for explanatory ownership.

### 4. Design decisions

Stable tradeoffs and owner decisions will be indexed at `design-decisions/index.md` after each candidate record is reconciled against the frozen architecture. Decision records explain why a boundary exists; they are not implementation logs. This track is **Planned — later review unit**.

### 5. Current status

| Reader question | Owner page | Availability |
| --- | --- | --- |
| What is supported on current `main`? | `status/current-state.md` | **Planned — later review unit** |
| What currently blocks or limits use? | `status/limitations-and-bottlenecks.md` | **Planned — later review unit** |
| What improvements are being considered? | `status/future-improvements.md` | **Planned — later review unit** |

Status pages describe reader-relevant capability boundaries. They must not become sprint plans, migration ledgers, phase reports, or package-by-package development histories.

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

When architectural detail is not an established owner decision, documentation labels it as:

- `DERIVED_CONSEQUENCE` — follows necessarily from established decisions;
- `IMPLEMENTATION_CHOICE` — may vary without changing architectural meaning;
- `OPEN_OWNER_DECISION` — requires explicit owner resolution.

## Public and local documentation boundary

The canonical reader journey contains concepts, architecture, references, stable design decisions, and a small set of current-status pages.

Audits, prompts, recovery inventories, migration ledgers, phase reports, review packs, verification runs, temporary blockers, source-level orientation, testing workflow, and pull-request process belong in the repository's ignored local development area. They are intentionally excluded from this navigation and are not linked from public pages.

Existing tracked documentation outside the journey above is transition input pending classification, reconciliation, and human review. It may contain useful material, stale implementation claims, or superseded architecture; do not treat it as canonical by default.
