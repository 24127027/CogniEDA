# Execution

The `execution` package is responsible for executing work delegated by the Planner.

It serves as the runtime bridge between planning and specialist executors. Once the Planner has selected a Task and prepared an execution request, the execution layer dispatches it to the appropriate executor, manages its lifecycle, and returns the result.

The execution layer **does not perform planning or domain reasoning**. It executes only what the Planner has already decided.

## Responsibilities

The execution layer is responsible for:

- Running the Planner workflow
- Dispatching execution requests to specialist executors
- Managing execution lifecycle
- Collecting execution results
- Reporting execution status
- Returning results to the application layer

In short, it answers the question:

> **How is a planned task executed?**

while the Planner answers:

> **What should be executed?**

## Responsibilities that do NOT belong here

The execution layer should never contain:

- research planning
- hypothesis generation
- task decomposition
- task prioritization
- workflow orchestration
- scientific reasoning

Executors are expected to be stateless specialists that perform isolated work and return structured results.

## Typical Execution Flow

```
Planner
    │
    ▼
Execution
    │
    ├── Select executor
    ├── Build execution request
    ├── Execute task
    └── Return result
```

Execution begins only after the Planner has approved a task for execution.

## Design Principles

- Planner-driven execution
- Stateless executors
- Deterministic dispatch
- Infrastructure-oriented
- Structured execution results

## Relationship to Other Packages

```
execution
    │
    ├── agents
    ├── messaging
    └── events
```

The execution package coordinates specialist executors but does not determine research direction.

## Package Structure

```
execution/
    executor_dispatcher.py
    planner_runner.py
```

- `planner_runner.py` runs the Planner workflow.
- `executor_dispatcher.py` dispatches execution requests to specialist executors.