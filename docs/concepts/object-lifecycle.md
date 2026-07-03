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
| `Hypothesis` | `proposed`, `testing`, `completed`, `invalidated`, `archived` | Implemented locally. |
| `Evidence` | `active`, `superseded`, `invalidated` | Implemented locally; records are immutable. |
| `Discovery` | Epistemic status: `supported`, `contradicted`, `inconclusive`, `insufficient_evidence` | Implemented locally; lifecycle flagging is not yet modeled. |
| `SessionFrame` | `active`, `checkpoint`, `handoff`, `superseded`, `archived` | Partially implemented. |

## Missing Lifecycle Guards

No code was found for:

- planner operation approval before durable Task creation
- Discovery invalidation/flagging lifecycle
- DataProfile supersession propagation
- Evidence supersession propagation
- automatic Assumption contradiction review after Discovery creation
- migration of older local databases to the current uniqueness constraints

Current local guards found:

- `HypothesisRepository.create()` enforces active terminal analytical Task admission and one Task to one Hypothesis.
- `DiscoveryRepository.create()` enforces active same-Hypothesis Evidence and one Hypothesis to one Discovery.
- `AssumptionRepository.flag_for_contradiction()` flags an Assumption for review and records the contradicting Discovery id without rewriting the assumption statement.

## Development Guidance

When adding lifecycle behavior, prefer typed state transitions and tests over informal status changes. Do not add an `update()` method to append-only objects unless the update is an allowed lifecycle transition with traceable provenance.
