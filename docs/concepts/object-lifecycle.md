# Object Lifecycle

## Target Design

Target lifecycle states:

| Object | Target lifecycle |
| --- | --- |
| `Objective` | `active -> completed / archived` |
| `DataProfile` | `draft -> active -> superseded / archived` |
| `Assumption` | `proposed -> active -> flagged -> retained / replaced / archived`; `proposed -> archived` |
| `Task` | `proposed -> active -> completed`; `proposed -> rejected`; `active -> paused -> active`; `active -> failed`; `active -> cancelled` |
| `Hypothesis` | `proposed -> testing -> confirmed / rejected / inconclusive`; `proposed -> cancelled` |
| `Evidence` | `created -> superseded / invalidated` |
| `Discovery` | `created -> flagged -> retained / deprecated / invalidated` |
| `SessionFrame` | `active -> closed` |
| `PlannerOperation` | `pending -> approved / rejected -> committed` |

Flagging is not mutation of truth. It is a review signal.

## Current Implementation

Current enums in `src/schemas/enums.py`:

| Current object | Current lifecycle/status enum | Status vs target |
| --- | --- | --- |
| `Project` | `active`, `paused`, `archived` | Implementation deviates from target because `Project` is not a target FCO. |
| `DataProfile` | No lifecycle enum; repository is append-only. | Partially implemented. |
| `Assumption` | `active`, `validated`, `rejected`, `archived` | Implementation deviates from target lifecycle. |
| `Hypothesis` | `proposed`, `planned`, `validating`, `supported`, `refuted`, `inconclusive`, `archived` | Partially implemented, but target names differ and no Task/Discovery cardinality is enforced. |
| `Evidence` | No lifecycle enum; repository is append-only. | Partially implemented; no superseded/invalidated state. |
| `DecisionLog` | `active`, `superseded`, `rejected`, `archived` | Implementation deviates because `DecisionLog` is not a target FCO. |
| `SessionFrame` | `active`, `checkpoint`, `handoff`, `superseded`, `archived` | Partially implemented; target lifecycle is simpler and user-governed item state is missing. |

## Missing Lifecycle Guards

No code was found for:

- proposed Task execution prevention
- active terminal Task readiness checks
- one Task to one Hypothesis
- one Hypothesis to one Discovery
- Discovery invalidation/flagging
- DataProfile supersession propagation
- Evidence supersession propagation
- Assumption contradiction review after Discovery creation

## Development Guidance

When adding lifecycle behavior, prefer typed state transitions and tests over informal status changes. Do not add an `update()` method to append-only objects unless the update is an allowed lifecycle transition with traceable provenance.
