# Orchestrator

The `orchestrator` package coordinates the lifecycle of an application request.

It serves as the boundary between external interfaces (such as the UI or API) and the internal agent system. The orchestrator translates incoming requests into runtime state, invokes the appropriate agents, coordinates application services, and produces the final response.

The orchestrator manages execution sequencing but never performs research planning or domain reasoning. Those responsibilities belong to the Planner and specialist agents.

## Responsibilities

The orchestrator is responsible for:

- Receiving application requests
- Validating and preprocessing requests
- Loading runtime context
- Constructing agent state
- Invoking the Planner
- Dispatching specialist executors when requested by the Planner
- Coordinating persistence
- Publishing runtime events
- Producing application responses

In short, it answers the question:

> **How should this application request be executed?**

while the Planner answers:

> **What should be done to satisfy the user's request?**

## Responsibilities that do NOT belong here

The orchestrator should never contain:

- research planning
- hypothesis generation
- task decomposition
- scientific reasoning
- domain-specific decision making
- tool implementations

The orchestrator coordinates execution but does not decide research direction.

## Typical Request Flow

```
UI / API
      │
      ▼
Orchestrator
      │
      ├── Validate request
      ├── Load runtime context
      ├── Build Planner state
      ├── Invoke Planner
      ├── Persist changes
      ├── Publish events
      └── Build response
      │
      ▼
UI / API
```

The orchestrator owns the request lifecycle from external input to external response.

## Design Principles

- Thin coordination layer
- Clear system boundary
- No domain knowledge
- No scientific reasoning
- Infrastructure-oriented
- Deterministic request lifecycle

## Relationship to Other Packages

```
UI / API
      │
      ▼
orchestrator
      │
      ├── execution
      ├── events
      ├── repositories
      ├── memory
      └── agents
```

The orchestrator coordinates these subsystems without owning their behavior.

## Package Structure

```
orchestrator/
    application_orchestrator.py
    request_pipeline.py
    response_pipeline.py
```

- `application_orchestrator.py` coordinates the overall request lifecycle.
- `request_pipeline.py` prepares runtime context and constructs the initial agent state.
- `response_pipeline.py` converts the final agent state into an application response and performs any required post-processing.