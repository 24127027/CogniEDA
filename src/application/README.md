# Application Layer

## Current implementation

Only `application/orchestrator/` contains runtime Python modules. It owns the durable execution-attempt protocol after planner approval:

- build and commit execution-admission operations;
- create/claim/release/cancel execution attempts through one transition owner;
- dispatch pending outbox work to an injected executor;
- receive and digest executor results into a durable inbox;
- claim/reclaim finalization with fencing;
- create the narrow deterministic scientific artifact bundle;
- reconcile pending inbox items and expired leases.

This package does **not** currently provide a root application service, UI/API request pipeline, event bus, CLI, worker daemon, or dependency container. `bootstrap/` and `events/` contain target-design READMEs only.

## Ownership boundary

The application layer coordinates persistence and execution state. It must not invent research claims. Scientific `Evidence` and `Discovery` are created only through the validated scientific-processing boundary and repository invariants.

The current worker path is independent of the compiled planner graph:

```text
planner approval/commit -> ExecutionRun + outbox
external worker loop     -> dispatch -> inbox
finalizer                -> scientific operations + attempt transition
```

## Target design

A future application shell may validate external requests, load context, invoke the planner, run worker loops, publish events and construct responses. None of that shell should be read as implemented until Python modules and tests exist.

See [orchestrator/README.md](orchestrator/README.md).
