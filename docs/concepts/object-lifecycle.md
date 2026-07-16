# Object Lifecycle

## Target Design

Flagging is not mutation of truth. It is a review signal.

## Current Implementation

Current enums in `src/schemas/enums.py`:

| Object | Current lifecycle/status enum | Status |
| --- | --- | --- |
| `Objective` | `active`, `paused`, `completed`, `archived` | Implemented locally. |
| `DataProfile` | `draft`, `active`, `superseded`, `archived` | Implemented locally; records are immutable. |
| `Assumption` | `proposed`, `active`, `flagged`, `retained`, `replaced`, `archived` | Partially implemented; source, testability, scope, scoped DataProfiles, contradiction refs, and replacement refs exist. |
| `Task` | `proposed`, `active`, `paused`, `completed`, `failed`, `rejected`, `cancelled` | Implemented locally. Proposed Tasks can appear in planning SessionFrame context but cannot generate Hypotheses. |
| `Hypothesis` | `proposed`, `approved`, `testing`, `awaiting_additional_evidence`, `ready_for_evaluation`, `confirmed`, `contradicted`, `inconclusive`, `insufficient_evidence`, `failed`, `cancelled`, `archived` | Implemented locally; execution/scientific paths use a subset of these transitions. |
| `Evidence` | `active`, `historically_scoped`, `superseded`, `invalidated` | Implemented locally; records are immutable. |
| `Discovery` | Lifecycle: `active`, `flagged`, `invalidated`, `deprecated`; epistemic status: `supported`, `contradicted`, `inconclusive`, `insufficient_evidence` | Partially implemented; repository-level flagging records review metadata without rewriting the claim, Evidence links, validity basis, or epistemic status. |
| `SessionFrame` | `active`, `checkpoint`, `handoff`, `superseded`, `archived` | Partially implemented. |

## Missing Lifecycle Guards

No code was found for:

- general planner approval before durable non-execution Task/plan/conflict changes
- full Discovery user-review workflow
- atomic DataProfile supersession propagation (repository-level historical scoping exists but commits in multiple steps)
- full runtime Evidence supersession propagation beyond the optional repository-level Discovery review flag
- automatic Assumption contradiction review after Discovery creation
- migration of older local databases to the current uniqueness constraints

Current local guards found:

- `HypothesisRepository.create()` enforces active terminal analytical Task admission and one Task to one Hypothesis.
- `DiscoveryRepository.create()` enforces active same-Hypothesis Evidence and one Hypothesis to one Discovery.
- `DiscoveryRepository.flag_by_evidence_change()` flags Discoveries for review after referenced Evidence is superseded or invalidated, while preserving the original claim and validity metadata.
- `AssumptionRepository.flag_for_contradiction()` flags an Assumption for review and records the contradicting Discovery id without rewriting the assumption statement.
- `DataProfileRepository.supersede()` can mark related Evidence historically scoped and flag related Discoveries when same-session repositories are supplied, but the full sequence is not atomic.

## Development Guidance

When adding lifecycle behavior, prefer typed state transitions and tests over informal status changes. Do not add an `update()` method to append-only objects unless the update is an allowed lifecycle transition with traceable provenance.
