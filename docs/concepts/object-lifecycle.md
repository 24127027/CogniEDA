# Object Lifecycle

## Target Design

Flagging is not mutation of truth. It is a review signal.

## Current Implementation

Current enums in `src/schemas/enums.py`:

| Object | Current lifecycle/status enum | Status |
| --- | --- | --- |
| `Objective` | `active`, `paused`, `completed`, `archived` | Implemented locally. |
| `DataProfile` | `draft`, `active`, `superseded`, `archived` | Implemented locally; records are immutable. |
| `Assumption` | `active`, `validated`, `rejected`, `archived` | Partially implemented. |
| `Task` | `active`, `paused`, `completed`, `failed`, `cancelled` | Implemented locally. Durable proposed/rejected Task states are not used. |
| `Hypothesis` | `proposed`, `testing`, `completed`, `invalidated`, `archived` | Implemented locally. |
| `Evidence` | `active`, `superseded`, `invalidated` | Implemented locally; records are immutable. |
| `Discovery` | Epistemic status: `supported`, `contradicted`, `inconclusive`, `insufficient_evidence` | Implemented locally; lifecycle flagging is not yet modeled. |
| `SessionFrame` | `active`, `checkpoint`, `handoff`, `superseded`, `archived` | Partially implemented. |

## Missing Lifecycle Guards

No code was found for:

- planner operation approval before durable Task creation
- database uniqueness for one Task to one Hypothesis
- database uniqueness for one Hypothesis to one Discovery
- Discovery invalidation/flagging lifecycle
- DataProfile supersession propagation
- Evidence supersession propagation
- Assumption contradiction review after Discovery creation

## Development Guidance

When adding lifecycle behavior, prefer typed state transitions and tests over informal status changes. Do not add an `update()` method to append-only objects unless the update is an allowed lifecycle transition with traceable provenance.
