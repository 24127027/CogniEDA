# SessionFrame

## Target Design

`SessionFrame` is the active context FCO. It is not long-term memory and not scientific knowledge. It is the user-governed working set exposed to the agent.

Target `SessionFrame` includes visible context items with object ID, object type, inclusion reason, added-by, user removability, and audit note.

## Current Implementation

The current `SessionFrame` model is in `src/schemas/artifacts.py`. It includes:

- `session_frame_id`
- `frame_topic`
- `frame_status`
- `objective_snapshot`
- optional outcome, objective summary, branch key, checkpoint label, parent frame ID, and handoff summary
- DataProfile, Task, Assumption, Hypothesis, Discovery, Evidence, and UserDecision summaries
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
- compact frame construction from target FCOs and user-decision provenance
- basic planning-vs-conclusion projection from a frame snapshot
- stale-context, dead-end, cached-tool-result, and invalidation metadata
- tests for repository round trips and builder behavior

Not yet implemented:

- target `context_items` structure
- target inclusion reasons and audit notes per item
- user-governed pin/remove/reorder/exclude behavior
- explicit active vs excluded object ID sets
- graph/retrieval policy that filters by epistemic role

## Known Deviation

The current `SessionFrame` is snapshot-oriented. The target design is more explicitly user-governed and object-item-oriented.
