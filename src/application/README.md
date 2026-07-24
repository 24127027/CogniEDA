# Application Layer

## Current implementation

`application/runtime.py` is the supported Wave 1 composition root. It requires a database URL,
authenticated-principal resolver, Hypothesis Analyst model, Data Explorer factory, and executor
context factory. Missing adapters fail closed. `runtime_loader.py` loads an explicit deployment
factory; it does not synthesize defaults.

`application/orchestrator/` owns the durable protocol after planner approval:

- build and commit execution-admission operations;
- create/claim/release/cancel execution attempts through one transition owner;
- dispatch pending outbox work to an injected executor;
- receive and digest executor results into a durable inbox;
- claim/reclaim Evidence admission with fencing;
- atomically create AnalysisFrame and immutable Evidence from canonical observations;
- build and evaluate a protected bundle, persist the exact proposal and governance decision, and
  atomically admit Discovery and its companion lifecycle/frame writes;
- atomically propagate validity events and exclude invalid state from active retrieval;
- reconcile pending inbox items and expired leases.

There is no supported package CLI or checked-in admission command. There is also no default
authentication implementation, concrete Data Explorer, service API, event bus, or worker daemon.
`bootstrap/` and `events/` remain target-design READMEs.

## Ownership boundary

The application layer coordinates persistence and workflow state. It does not evaluate p-values or
invent claims. Evidence is authored only by the atomic Evidence-admission transaction. Discovery
content is copied exactly from the protected Hypothesis Analyst proposal by atomic Discovery
admission after durable governance.

The current worker path is independent of the compiled planner graph:

```text
planner approval/commit  -> ExecutionRun + outbox
external worker loop      -> Data Explorer -> observation-only inbox
Evidence admission        -> AnalysisFrame + Evidence
Hypothesis Analyst        -> protected proposal
governance + admission    -> Discovery + lifecycle + conclusion frame
validity propagation      -> dependent invalidation/review + retrieval exclusion
```

## Target design

A future deployment shell may validate external requests, run worker loops, publish events and
construct responses. The composition contract exists; concrete deployment adapters do not.

See [orchestrator/README.md](orchestrator/README.md).
