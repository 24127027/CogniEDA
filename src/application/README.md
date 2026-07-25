# Application Layer

## Current implementation

`application/runtime.py` is the supported Wave 1 composition root. It requires a database URL,
authenticated-principal resolver, Hypothesis Analyst model, Data Explorer factory, and executor
identifier/context factory. The identifier must exactly match durable admitted work; current
analytical contracts use `deterministic`. Missing adapters fail closed. `runtime_loader.py` loads an explicit deployment
factory; it does not synthesize defaults.

Following **Package S2-A**, application responsibilities are structured into focused bounded contexts:

- `application/execution/`: Owns execution attempt admission, contract/receipt identity hashing, transition service, dispatching, receipt ingestion, cancellation, and recovery.
- `application/evidence/`: Owns pure Evidence admission plan validation and the atomic AnalysisFrame + Evidence write transaction.
- `application/evaluation/`: Owns protected synthesis bundle construction, evaluation transition state machine, CAS fencing, and evaluator runner invocation.
- `application/governance/`: Owns authenticated principal resolution, governance authority issuance, durable proposal decision recording, and deterministic governance fingerprints.
- `application/orchestrator/`: Temporarily retains atomic Discovery admission and validity propagation.

There is no supported package CLI or checked-in admission command. There is also no default
authentication implementation, concrete Data Explorer, service API, event bus, or worker daemon.
`bootstrap/` and `events/` remain target-design READMEs.

## Ownership boundary

The application layer coordinates persistence and workflow state. It does not evaluate p-values or
invent claims. Evidence is authored only by the atomic Evidence-admission transaction (`application.evidence.admission_service`). Discovery
content is copied exactly from the protected Hypothesis Analyst proposal by atomic Discovery
admission after durable governance.

The current worker path is independent of the compiled planner graph:

```text
planner approval/commit  -> ExecutionRun + outbox (application.execution)
external worker loop      -> Data Explorer -> observation-only inbox (application.execution)
Evidence admission        -> AnalysisFrame + Evidence (application.evidence)
Hypothesis Analyst        -> protected proposal (application.evaluation)
governance decision       -> durable proposal decision (application.governance)
atomic admission          -> Discovery + lifecycle + conclusion frame (application.orchestrator)
validity propagation      -> dependent invalidation/review + retrieval exclusion (application.orchestrator)
```

## Target design

A future deployment shell may validate external requests, run worker loops, publish events and
construct responses. The composition contract exists; concrete deployment adapters do not.

See [execution/README.md](execution/README.md), [evidence/README.md](evidence/README.md), [evaluation/README.md](evaluation/README.md), [governance/README.md](governance/README.md), and [orchestrator/README.md](orchestrator/README.md).
