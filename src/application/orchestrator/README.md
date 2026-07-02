# Orchestrator

The `orchestrator` package coordinates the execution of an application request.

It manages the overall execution flow by invoking the appropriate subsystems in the correct order. The orchestrator owns execution sequencing but never performs scientific reasoning or workflow planning.

Research decisions remain the responsibility of the Planner.

## Responsibilities

- Receive application requests
- Load runtime context
- Invoke the Planner
- Dispatch specialist executors
- Coordinate persistence
- Publish runtime events
- Produce application responses

## Does NOT contain

- Hypothesis generation
- Task decomposition
- Statistical reasoning
- Domain knowledge
- Tool implementations

The orchestrator answers:

> How should this request be executed?

The Planner answers:

> What should be done?