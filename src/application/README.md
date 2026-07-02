# Application

The `application` package is the runtime coordination layer of CogniEDA.

It owns the lifecycle of an application request and serves as the boundary between external interfaces (such as the UI or API) and the internal agent system. The application layer coordinates planners, executors, persistence, events, tools, and other infrastructure to execute a request from start to finish.

The application layer **does not contain research logic or domain reasoning**. Those responsibilities belong to the Planner and specialist agents.

Instead, the application layer ensures that the appropriate components are invoked in the correct order and that runtime state is coordinated consistently.

## Responsibilities

The application layer is responsible for:

- Receiving requests from external interfaces
- Validating and preprocessing requests
- Loading runtime context
- Constructing agent state
- Invoking the Planner
- Dispatching specialist executors
- Coordinating persistence
- Publishing runtime events
- Producing responses for external interfaces

In short, it answers the question:

> **How should the application execute this request?**

while the Planner answers:

> **What should be done to satisfy the user's request?**

## Responsibilities that do NOT belong here

The application layer should never contain:

- research planning
- hypothesis generation
- task decomposition
- scientific reasoning
- statistical interpretation
- domain-specific decision making

These belong to the Planner or specialist agents.

Likewise, the application layer should not implement storage engines, databases, tool implementations, or memory systems directly. Those belong to their respective packages.

## Typical Request Flow

```
UI / API
      │
      ▼
Application
      │
      ├── Validate request
      ├── Load runtime context
      ├── Construct agent state
      ├── Invoke Planner
      ├── Persist state changes
      ├── Publish events
      └── Produce response
      │
      ▼
UI / API
```

The application layer owns the request lifecycle but never determines research direction.

## Design Principles

- Thin coordination layer
- Clear system boundary
- No domain knowledge
- No scientific reasoning
- Infrastructure-oriented
- Deterministic request lifecycle
- Composes subsystems instead of implementing them

## Package Structure

```
application/
    bootstrap/
    orchestrator/
    events/
```

- `bootstrap/` initializes and wires application dependencies.
- `orchestrator/` coordinates the lifecycle of an application request.
- `events/` provides the application's internal event system.

## Relationship to Other Packages

```
                UI / API
                    │
                    ▼
             application
                    │
     ┌──────────────┼──────────────┐
     ▼              ▼              ▼
  agents       repositories      events
     │              │
     ├────── memory ──────┤
     │
    tools
```

The application layer coordinates these subsystems while keeping them independent and reusable.