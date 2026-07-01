# SessionFrame

## Target Design

`SessionFrame` is the active context FCO. It is not long-term memory and not scientific knowledge. It is the user-governed working set exposed to the agent.

Target `SessionFrame` includes:

- `session_id`
- lifecycle state: `active` or `closed`
- pinned object IDs
- active object IDs
- excluded object IDs
- ordering
- context items with object ID, object type, inclusion reason, added-by, user removability, and audit note

The target workflow expects a visible panel where users can inspect, pin, remove, reorder, or audit why context items were included.

## Current Implementation

The current `SessionFrame` model is in `src/schemas/artifacts.py`. It includes:

- `session_frame_id`
- `project_id`
- `frame_topic`
- `frame_status`
- `objective_snapshot`
- optional outcome, project summary, branch key, checkpoint label, parent frame ID, and handoff summary
- dataset, assumption, hypothesis, evidence, and decision summaries
- pending task strings and open question strings
- warnings, stale context, dead ends, cached tool-result summaries, and invalidation rules
- `created_at`

Persistence is implemented by `SessionFrameRepository`. Construction is implemented by `SessionFrameBuilder`.

`SessionContextBuilder` can derive non-persistent `planning` and `conclusion` context bundles from a persisted `SessionFrame`. This is a guard for prompt/context assembly, not a new durable object.

## Implementation Status

Partially implemented.

Implemented:

- append-only repository surface
- latest/recent frame queries
- compact frame construction from current artifacts
- basic planning-vs-conclusion projection from a frame snapshot
- stale-context, dead-end, cached-tool-result, and invalidation metadata
- tests for repository round trips and builder behavior

Not yet implemented:

- target `context_items` structure
- target inclusion reasons and audit notes per item
- user-governed pin/remove/reorder/exclude behavior
- explicit active vs excluded object ID sets
- graph/retrieval policy that filters by epistemic role
- `Task` and `Discovery` references, because those objects do not yet exist

## Known Deviation

The current `SessionFrame` is project-scoped and snapshot-oriented. The target design is session-scoped and object-item-oriented. Current behavior is useful as a scaffold, but docs and future code should not claim it fully enforces target context governance.
