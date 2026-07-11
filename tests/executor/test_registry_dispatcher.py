from __future__ import annotations

import asyncio

import pytest
from pydantic import ValidationError

from agents.executor import (
    Capability,
    ExecutionRequest,
    ExecutionResult,
    ExecutorContext,
    ExecutorDispatcher,
    ExecutorInput,
    ExecutorRegistry,
    Task,
    build_capability_selection_instructions,
    build_capability_selection_model,
    executor_registry,
)
from agents.executor.executor import Executor
from agents.executor.types import BaseState
from agents.planner.types import PlannerOutput


class FakeGraph:
    def __init__(self) -> None:
        self.calls: list[tuple[ExecutorInput, ExecutorContext]] = []

    async def ainvoke(
        self,
        input: ExecutorInput,
        context: ExecutorContext,
    ) -> dict[str, object]:
        self.calls.append((input, context))
        return {
            "evidence_drafts": [{"kind": "draft"}],
            "discovery_drafts": [],
            "execution_run_ref": "execution-run:test",
        }


class GraphBackedExecutor(Executor[BaseState]):
    def __init__(self) -> None:
        self.fake_graph = FakeGraph()
        super().__init__(lambda: self.fake_graph)


class FakeExecutor(Executor[BaseState]):
    instance_count = 0

    def __init__(self) -> None:
        FakeExecutor.instance_count += 1
        self.calls: list[tuple[ExecutorInput, ExecutorContext]] = []
        self.result = ExecutionResult()

    async def run(
        self,
        input: ExecutorInput,
        context: ExecutorContext,
    ) -> ExecutionResult:
        self.calls.append((input, context))
        return self.result


def test_registry_reuses_lazy_singleton() -> None:
    FakeExecutor.instance_count = 0
    registry = ExecutorRegistry()

    registry.register(Capability.GRAPH_MINING)(FakeExecutor)

    first = registry.get(Capability.GRAPH_MINING.id)
    second = registry.get(Capability.GRAPH_MINING.id)

    assert first is second
    assert FakeExecutor.instance_count == 1


def test_registry_rejects_duplicate_capability() -> None:
    registry = ExecutorRegistry()
    registry.register(Capability.GRAPH_MINING)(FakeExecutor)

    with pytest.raises(ValueError, match="Capability already registered: graph_mining"):
        registry.register(Capability.GRAPH_MINING)(FakeExecutor)


def test_registry_reports_unknown_capability() -> None:
    registry = ExecutorRegistry()

    with pytest.raises(KeyError, match="No executor registered for capability: missing"):
        registry.get("missing")


def test_registry_lists_capability_specs() -> None:
    registry = ExecutorRegistry()

    registry.register(Capability.GRAPH_MINING)(FakeExecutor)

    assert registry.get_spec(Capability.GRAPH_MINING.id) is Capability.GRAPH_MINING
    assert registry.list_specs() == (Capability.GRAPH_MINING,)


def test_dispatcher_invokes_registered_executor() -> None:
    registry = ExecutorRegistry()
    registry.register(Capability.GRAPH_MINING)(FakeExecutor)
    dispatcher = ExecutorDispatcher(registry)
    executor = registry.get(Capability.GRAPH_MINING.id)
    request = ExecutionRequest(
        capability=Capability.GRAPH_MINING.id,
        input=ExecutorInput(task=Task()),
        context=ExecutorContext(),
    )

    result = asyncio.run(dispatcher.dispatch(request))

    assert result is executor.result
    assert executor.calls == [(request.input, request.context)]


def test_execution_request_rejects_unknown_capability() -> None:
    with pytest.raises(ValidationError, match="Unknown executor capability"):
        ExecutionRequest(
            capability="missing",
            input=ExecutorInput(task=Task()),
            context=ExecutorContext(),
        )


def test_planner_output_validates_nested_execution_request_capability() -> None:
    with pytest.raises(ValidationError, match="Unknown executor capability"):
        PlannerOutput(
            execution_request={
                "capability": "missing",
                "input": {"task": {}},
                "context": {},
            }
        )


def test_capability_selection_model_restricts_to_explicit_subset() -> None:
    selection_model = build_capability_selection_model((Capability.GRAPH_MINING,))

    valid = selection_model(capability=Capability.GRAPH_MINING.id)

    assert valid.capability == Capability.GRAPH_MINING.id
    with pytest.raises(ValidationError):
        selection_model(capability=Capability.HYPOTHESIS_TESTING.id)


def test_capability_selection_instructions_render_explicit_subset() -> None:
    instructions = build_capability_selection_instructions((Capability.GRAPH_MINING,))

    assert Capability.GRAPH_MINING.id in instructions
    assert Capability.HYPOTHESIS_TESTING.id not in instructions
    assert "`capability`" in instructions


def test_executor_run_returns_validated_graph_execution_result() -> None:
    executor = GraphBackedExecutor()
    input = ExecutorInput(task=Task())
    context = ExecutorContext()

    result = asyncio.run(executor.run(input=input, context=context))

    assert result == ExecutionResult(
        evidence_drafts=[{"kind": "draft"}],
        discovery_drafts=[],
        execution_run_ref="execution-run:test",
    )
    assert executor.fake_graph.calls == [(input, context)]


def test_executor_package_initializes_existing_default_executors() -> None:
    registered = {spec.id for spec in executor_registry.list_specs()}

    assert {Capability.GRAPH_MINING.id, Capability.HYPOTHESIS_TESTING.id} <= registered
