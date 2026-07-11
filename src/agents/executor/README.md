# Executor Dispatch Architecture

This document describes the executor dispatch code that exists now. Future
planner or delegation behavior is labeled separately and should not be read as
implemented runtime behavior.

## What exists now

Executor dispatch currently lives in `src/agents/executor/dispatcher.py`.
It is a thin adapter around `ExecutorRegistry` and `ExecutionRequest`.

The implemented objects are:

| Object | Location | Current role |
| --- | --- | --- |
| `ExecutionRequest` | `src/agents/executor/types.py` | Pydantic request containing `capability`, `input`, and `context`. |
| `ExecutionResult` | `src/agents/executor/types.py` | Validated executor return type; concrete draft/provenance fields are not implemented yet. |
| `ExecutorRegistry` | `src/agents/executor/registry.py` | Stores capability specs, executor factories, and lazy singleton executor instances. |
| `ExecutorDispatcher` | `src/agents/executor/dispatcher.py` | Resolves a capability id through the registry and calls the executor. |
| `CapabilitySpec` / `Capability` | `src/agents/executor/capabilities.py` | Defines canonical capability ids and descriptions. |

`ExecutionRequest` validates `capability` at the Pydantic boundary against
`CAPABILITY_IDS`. That confirms the id is part of the canonical capability
catalog. It does not prove an executor is registered or runnable for that id.

The current capability catalog and registration status are:

| Capability id | Catalog status | Registered executor |
| --- | --- | --- |
| `data_exploration` | Catalogued | Not registered |
| `graph_mining` | Catalogued | `GraphMiner` |
| `hypothesis_testing` | Catalogued | `HypothesisAnalyst` |

Concrete executors self-register in their agent modules with
`@executor_registry.register(...)`:

- `GraphMiner` registers `graph_mining` in
  `src/agents/executor/graph_miner/agent.py`.
- `HypothesisAnalyst` registers `hypothesis_testing` in
  `src/agents/executor/hypothesis_analyst/agent.py`.

The registered wrappers exist, but their graph builders still raise
`NotImplementedError`. Basic registry and dispatcher plumbing exists; the
default executor graphs are scaffold-level.

Planner integration is also scaffold-level. `src/agents/planner/graph.py` has
execution-shaped edges, but `prepare_execution`, `dispatch_executor`, and
`review_execution` in `src/agents/planner/nodes.py` are stubs, and
`src/agents/planner/types.py` does not define a dispatcher field on planner
runtime `Context`.

## How dispatch actually works

`ExecutorDispatcher.dispatch(request)` performs only this flow:

1. Read `request.capability`.
2. Resolve the capability id with `ExecutorRegistry.get(...)`.
3. Call `executor.run(input=request.input, context=request.context)`.
4. Return the `ExecutionResult`.

The core implementation is:

```python
executor = self._registry.get(request.capability)

return await executor.run(
    input=request.input,
    context=request.context,
)
```

The dispatcher does not:

- choose among executors based on caller permissions
- build `ExecutorInput`
- build `ExecutorContext`
- validate the full execution request beyond the `ExecutionRequest` model
- authorize callers
- route executor-to-executor delegation
- trace delegation
- retry failures
- enforce cycle or depth limits

`ExecutorRegistry.get(capability_id)` raises `KeyError` when the capability id
has no registered executor. This can happen even when `ExecutionRequest`
accepted the id, because `ExecutionRequest` validates against the capability
catalog while the registry resolves only registered capabilities.

## What selection helpers do

The selection helpers constrain an LLM to choose one capability id from an
allowed subset. They are only for capability choice.

`build_capability_selection_model(capabilities)` creates a Pydantic model with
one field:

```python
capability: Literal[<allowed capability ids>]
```

That selection model does not validate or construct the full
`ExecutionRequest`. The caller still builds `ExecutorInput` and
`ExecutorContext` by hand.

`build_capability_selection_instructions(capabilities)` creates prompt text
that tells a model to choose exactly one capability id from the same allowed
subset.

Minimal usage pattern:

```python
from pydantic_ai import Agent

from agents.executor import (
    ExecutionRequest,
    ExecutorContext,
    ExecutorInput,
    ExecutorDispatcher,
    build_capability_selection_instructions,
    build_capability_selection_model,
    executor_registry,
)
from agents.executor.capabilities import Capability

# 1) Let the LLM choose only the capability.
selection_model = build_capability_selection_model(executor_registry.list_specs())
selection_instructions = build_capability_selection_instructions(
    executor_registry.list_specs()
)

selector = Agent(
    model=model,
    result_type=selection_model,
    system_prompt=selection_instructions,
)

selection = await selector.run(
    "Use the specialist that can analyze graph structure."
)

# 2) Build the rest by hand.
request = ExecutionRequest(
    capability=selection.data.capability,
    input=ExecutorInput(task=task),
    context=ExecutorContext(),
)

# 3) Dispatch.
dispatcher = ExecutorDispatcher(executor_registry)
result = await dispatcher.dispatch(request)
```

In this example, `executor_registry.list_specs()` limits selection to registered
capability specs. With the default registry, that excludes catalogued but
unregistered capabilities such as `data_exploration`.

## What is not implemented yet

The following behavior is not live in the current code:

- Planner runtime ownership of a dispatcher instance.
- Implemented `prepare_execution`, `dispatch_executor`, or `review_execution`
  planner node bodies.
- Planner construction of `ExecutionRequest` from selected `Task` objects.
- Planner persistence of dispatch requests or results through atomic
  `PlannerOperation` records.
- Caller-scoped dispatcher authorization.
- Executor-to-executor delegation routing.
- Delegation tracing.
- Retry policy.
- Cycle/depth protection.
- Runnable default graphs for `GraphMiner` and `HypothesisAnalyst`.
- Registered executor for `data_exploration`.
- Concrete `ExecutionResult` fields for Evidence drafts, Discovery drafts, or
  execution-run provenance.

## Target behavior / future work

The target planner/executor design is for the planner to prepare an execution
request for an approved analytical task, dispatch it by capability id, review
the execution result, and commit any durable changes through the appropriate
operation/provenance path.

Future executor-to-executor delegation may use the same
`ExecutionRequest -> ExecutionResult` shape, but no delegation routing,
authorization, tracing, retry, or cycle/depth protection exists today. That work
must be designed and implemented before executor chains are treated as supported
runtime behavior.

## Related documents

- [Planner Workflow](planner-workflow.md)
- [First-Class Objects](first-class-objects.md)
- [Implementation Gap Analysis](implementation-gap-analysis.md)
