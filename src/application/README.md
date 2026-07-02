# Application

The `application` package is the runtime coordination layer of CogniEDA.

It owns the lifecycle of an application request and connects the major subsystems of the application, including planners, executors, tools, memory, repositories, and external services.

The application layer **does not contain research logic or domain reasoning**. Those responsibilities belong to the Planner and specialist agents.

Instead, this package is responsible for ensuring that every component is invoked in the correct order and that state changes are coordinated consistently.

## Responsibilities

The application layer is responsible for:

- Receiving user requests
- Loading runtime context (workspace, session, repositories)
- Invoking the Planner
- Dispatching specialist executors
- Managing application-level transactions
- Publishing and handling runtime events
- Persisting state changes
- Returning responses to the API or UI

In short, it answers the question:

> **How does the application execute a request?**

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

Likewise, this layer should not implement storage engines, databases, or tool logic directly. Those belong to their respective packages.

## Typical Request Flow

```
User Request
      │
      ▼
Application
      │
      ├── Load runtime context
      ├── Invoke Planner
      ├── Dispatch executor (if needed)
      ├── Commit state changes
      ├── Publish events
      └── Return response
```

The application layer coordinates execution but does not decide research direction.

## Design Principles

- Thin orchestration layer
- No domain knowledge
- No scientific reasoning
- Infrastructure-oriented
- Transactional and deterministic
- Composes subsystems instead of implementing them

## Relationship to Other Packages

```
application
    │
    ├── agents
    ├── memory
    ├── tools
    ├── mcp
    ├── repositories
    └── events
```

The application package sits above these components and coordinates them during execution.

Individual components remain independent and reusable.