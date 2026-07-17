from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from pydantic import ValidationError

from agents.executor import (
    Capability,
    ExecutorContext,
    ExecutorDispatcher,
    ExecutorInput,
    ExecutorRegistry,
    build_capability_selection_instructions,
    build_capability_selection_model,
    executor_registry,
)
from agents.executor.executor import Executor
from agents.executor.types import BaseState
from agents.planner.types import PlannerOutput
from application.orchestrator.execution_contracts import (
    AnalysisFrameObservation,
    ExecutionRunObservation,
    ExecutionSpecification,
    ExecutorResult,
    HypothesisDraft,
    PreparedExecution,
)
from schemas.common import EvaluationThresholds


def make_prepared_execution(executor_id: str = "graph_mining") -> PreparedExecution:
    task_id = uuid4()
    hypothesis_id = uuid4()
    profile_id = uuid4()
    return PreparedExecution(
        task_ref=str(task_id),
        hypothesis_ref=str(hypothesis_id),
        data_profile_ref=str(profile_id),
        task_title="test",
        dataset_path="dataset.csv",
        contract_fingerprint="abc",
        execution_run_id=uuid4(),
        dispatch_idempotency_key=str(uuid4()),
        lease_epoch=1,
        hypothesis=HypothesisDraft(
            statement="test",
            scope="test",
            validation_method="test",
            evidence_expectation="test",
        ),
        specification=ExecutionSpecification(
            claim_type="association",
            scope="test",
            evidence_expectation="test",
            decision_rule=EvaluationThresholds(p_value=0.05),
            validation_method="test",
            executor_id=executor_id,
        ),
    )


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
            "status": "failed",
            "error_message": "test error",
            "analysis_frame": {
                "frame_hash": "test",
            },
            "execution_run": {
                "status": "failed",
            },
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
        self.result = ExecutorResult(
            status="failed",
            error_message="test failure",
            analysis_frame=AnalysisFrameObservation(frame_hash="test"),
            execution_run=ExecutionRunObservation(status="failed"),
        )

    async def run(
        self,
        input: ExecutorInput,
        context: ExecutorContext,
    ) -> ExecutorResult:
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

    prepared = make_prepared_execution(Capability.GRAPH_MINING.id)
    context = ExecutorContext()

    result = asyncio.run(dispatcher.dispatch(prepared, context))

    assert result is executor.result
    assert len(executor.calls) == 1
    input_data = executor.calls[0][0]
    assert input_data.execution_run_id == prepared.execution_run_id
    assert str(input_data.task_id) == prepared.task_ref
    assert str(input_data.hypothesis_id) == prepared.hypothesis_ref
    assert str(input_data.data_profile_id) == prepared.data_profile_ref


def test_dispatcher_rejects_non_durable_identity_before_registry_resolution() -> None:
    dispatcher = ExecutorDispatcher(ExecutorRegistry())
    prepared = make_prepared_execution().model_copy(update={"execution_run_id": None})

    with pytest.raises(ValueError, match="ExecutionRun identity"):
        asyncio.run(dispatcher.dispatch(prepared, ExecutorContext()))


def test_registry_invokes_factory_lazily_and_propagates_factory_failure() -> None:
    registry = ExecutorRegistry()
    calls = 0

    def failing_factory():
        nonlocal calls
        calls += 1
        raise RuntimeError("factory failed")

    registry.register_factory(Capability.GRAPH_MINING, failing_factory)

    assert calls == 0
    with pytest.raises(RuntimeError, match="factory failed"):
        registry.get(Capability.GRAPH_MINING.id)
    assert calls == 1


def test_planner_output_cannot_embed_an_executor_request() -> None:
    """Planner model output must flow through planner admission, not executor dispatch."""

    planner_fields = set(PlannerOutput.model_fields)

    assert "execution_request" not in planner_fields
    assert {"planner_operations", "executor_dispatch_ref"} <= planner_fields


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
    prepared = make_prepared_execution()

    input_data = ExecutorInput(
        execution_run_id=prepared.execution_run_id,
        task_id=prepared.task_ref,
        hypothesis_id=prepared.hypothesis_ref,
        data_profile_id=prepared.data_profile_ref,
        dataset_path=prepared.dataset_path,
        hypothesis=prepared.hypothesis,
        specification=prepared.specification,
        deterministic_seed=prepared.deterministic_seed,
    )
    context = ExecutorContext()

    result = asyncio.run(executor.run(input=input_data, context=context))

    assert result.status == "failed"
    assert result.error_message == "test error"
    assert result.analysis_frame.frame_hash == "test"
    assert executor.fake_graph.calls == [(input_data, context)]


def test_executor_package_initializes_existing_default_executors() -> None:
    registered = {spec.id for spec in executor_registry.list_specs()}

    assert {Capability.GRAPH_MINING.id, Capability.HYPOTHESIS_TESTING.id} <= registered


def test_executor_scientific_input_excludes_planner_and_retrieval_context() -> None:
    assert {
        "assumptions",
        "task_motivation",
        "retrieval_scores",
        "session_frame",
        "raw_chat",
        "planner_state",
    }.isdisjoint(ExecutorInput.model_fields)


@pytest.mark.parametrize(
    "capability_id",
    [Capability.GRAPH_MINING.id, Capability.HYPOTHESIS_TESTING.id],
)
def test_registered_default_executor_graphs_fail_explicitly(capability_id: str) -> None:
    with pytest.raises(NotImplementedError):
        executor_registry.get(capability_id)
