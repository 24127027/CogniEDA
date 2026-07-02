# Orchestrator

The `orchestrator` package coordinates the lifecycle of an application request.

It transforms incoming requests into agent state, invokes the appropriate runtime components, coordinates persistence and event publication, and produces the final response.

The orchestrator manages execution sequencing but never performs research planning or domain reasoning. Those responsibilities belong to the Planner and specialist agents.

## Responsibilities

The orchestrator is responsible for:

- Validating incoming requests
- Loading runtime context
- Constructing agent state
- Invoking the Planner
- Dispatching specialist executors
- Coordinating persistence
- Publishing runtime events
- Producing application responses

In short, it answers the question:

> **How should this request be coordinated?**

## Typical Request Flow

```
Request
    │
    ▼
Orchestrator
    │
    ├── Validate request
    ├── Load runtime context
    ├── Construct agent state
    ├── Invoke Planner
    ├── Dispatch executors
    ├── Persist changes
    ├── Publish events
    └── Produce response
```

The orchestrator owns the request lifecycle but never determines research direction.

## Design Principles

- Thin coordination layer
- Deterministic execution
- No domain knowledge
- No scientific reasoning
- Infrastructure-oriented

## Package Structure

```
orchestrator/
    application_orchestrator.py
    request_pipeline.py
    response_pipeline.py
```

- `application_orchestrator.py` coordinates the overall request lifecycle.
- `request_pipeline.py` validates requests, loads runtime context, and constructs the initial agent state.
- `response_pipeline.py` performs post-processing and produces the final application response.