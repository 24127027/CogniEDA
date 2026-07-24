from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from pydantic import ValidationError

from agents.executor import (
    Capability,
    DataExplorerAdapter,
    DataExplorerDispatcher,
    DataExplorerExecutionContext,
    DataExplorerInput,
    DataExplorerRegistry,
    build_capability_selection_instructions,
    build_capability_selection_model,
)
from agents.executor.graph_miner.agent import GraphMiner
from agents.executor.hypothesis_analyst.agent import HypothesisAnalyst
from agents.executor.types import BaseState
from agents.planner.types import PlannerOutput
from application.orchestrator.execution_contracts import (
    ExecutionSpecification,
    HypothesisDraft,
    PreparedExecution,
)
from schemas.common import EvaluationThresholds
from schemas.specialist_contracts import (
    DataExplorerFailureReason,
    DataExplorerFailureResult,
    DataExplorerResult,
)


def make_prepared_execution(executor_id: str = "data_exploration") -> PreparedExecution:
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
        self.calls: list[tuple[DataExplorerInput, DataExplorerExecutionContext]] = []

    async def ainvoke(
        self,
        input: DataExplorerInput,
        context: DataExplorerExecutionContext,
    ) -> dict[str, object]:
        self.calls.append((input, context))
        return {
            "status": "failed",
            "failure_reason": DataExplorerFailureReason.METHOD_EXECUTION_FAILURE,
            "message": "test error",
        }


class GraphBackedExecutor(DataExplorerAdapter[BaseState]):
    def __init__(self) -> None:
        self.fake_graph = FakeGraph()
        super().__init__(lambda: self.fake_graph)


class FakeExecutor(DataExplorerAdapter[BaseState]):
    instance_count = 0

    def __init__(self) -> None:
        FakeExecutor.instance_count += 1
        self.calls: list[tuple[DataExplorerInput, DataExplorerExecutionContext]] = []
        self.result = DataExplorerFailureResult(
            status="failed",
            failure_reason=DataExplorerFailureReason.METHOD_EXECUTION_FAILURE,
            message="test failure",
        )

    async def run(
        self,
        input: DataExplorerInput,
        context: DataExplorerExecutionContext,
    ) -> DataExplorerResult:
        self.calls.append((input, context))
        return self.result


def test_registry_reuses_lazy_singleton() -> None:
    FakeExecutor.instance_count = 0
    registry = DataExplorerRegistry()

    registry.register(Capability.DATA_EXPLORATION)(FakeExecutor)

    first = registry.get(Capability.DATA_EXPLORATION.id)
    second = registry.get(Capability.DATA_EXPLORATION.id)

    assert first is second
    assert FakeExecutor.instance_count == 1


def test_registry_rejects_duplicate_capability() -> None:
    registry = DataExplorerRegistry()
    registry.register(Capability.DATA_EXPLORATION)(FakeExecutor)

    with pytest.raises(ValueError, match="Capability already registered: data_exploration"):
        registry.register(Capability.DATA_EXPLORATION)(FakeExecutor)


def test_registry_reports_unknown_capability() -> None:
    registry = DataExplorerRegistry()

    with pytest.raises(KeyError, match="No executor registered for capability: missing"):
        registry.get("missing")


def test_registry_lists_capability_specs() -> None:
    registry = DataExplorerRegistry()

    registry.register(Capability.DATA_EXPLORATION)(FakeExecutor)

    assert registry.get_spec(Capability.DATA_EXPLORATION.id) is Capability.DATA_EXPLORATION
    assert registry.list_specs() == (Capability.DATA_EXPLORATION,)


def test_dispatcher_invokes_registered_executor() -> None:
    registry = DataExplorerRegistry()
    registry.register(Capability.DATA_EXPLORATION)(FakeExecutor)
    dispatcher = DataExplorerDispatcher(registry)
    executor = registry.get(Capability.DATA_EXPLORATION.id)

    prepared = make_prepared_execution(Capability.DATA_EXPLORATION.id)
    context = DataExplorerExecutionContext()

    result = asyncio.run(dispatcher.dispatch(prepared, context))

    assert result is executor.result
    assert len(executor.calls) == 1
    input_data = executor.calls[0][0]
    assert input_data.execution_run_id == prepared.execution_run_id
    assert str(input_data.task_id) == prepared.task_ref
    assert str(input_data.hypothesis_id) == prepared.hypothesis_ref
    assert str(input_data.data_profile_id) == prepared.data_profile_ref


def test_dispatcher_rejects_non_durable_identity_before_registry_resolution() -> None:
    dispatcher = DataExplorerDispatcher(DataExplorerRegistry())
    prepared = make_prepared_execution().model_copy(update={"execution_run_id": None})

    with pytest.raises(ValueError, match="ExecutionRun identity"):
        asyncio.run(dispatcher.dispatch(prepared, DataExplorerExecutionContext()))


def test_registry_invokes_factory_lazily_and_propagates_factory_failure() -> None:
    registry = DataExplorerRegistry()
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

    input_data = DataExplorerInput(
        execution_run_id=prepared.execution_run_id,
        task_id=prepared.task_ref,
        hypothesis_id=prepared.hypothesis_ref,
        data_profile_id=prepared.data_profile_ref,
        dataset_path=prepared.dataset_path,
        hypothesis=prepared.hypothesis,
        specification=prepared.specification,
        deterministic_seed=prepared.deterministic_seed,
    )
    context = DataExplorerExecutionContext()

    result = asyncio.run(executor.run(input=input_data, context=context))

    assert result.status == "failed"
    assert result.message == "test error"
    assert result.failure_reason == DataExplorerFailureReason.METHOD_EXECUTION_FAILURE
    assert executor.fake_graph.calls == [(input_data, context)]


def test_dispatcher_runtime_seam_rejects_executor_scientific_authority() -> None:
    class MaliciousExecutor:
        async def run(
            self, input: DataExplorerInput, context: DataExplorerExecutionContext
        ) -> dict[str, object]:
            return {
                "status": "failed",
                "failure_reason": DataExplorerFailureReason.METHOD_EXECUTION_FAILURE,
                "message": "technical failure",
                "evaluation": {"outcome": "supports", "finalize": True},
            }

    registry = DataExplorerRegistry()
    registry.register_factory(Capability.DATA_EXPLORATION, MaliciousExecutor)

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        asyncio.run(
            DataExplorerDispatcher(registry).dispatch(
                make_prepared_execution(Capability.DATA_EXPLORATION.id),
                DataExplorerExecutionContext(),
            )
        )


def test_graph_miner_and_hypothesis_analyst_are_not_data_explorer_executors() -> None:
    assert not issubclass(GraphMiner, DataExplorerAdapter)
    assert not issubclass(HypothesisAnalyst, DataExplorerAdapter)


@pytest.mark.parametrize(
    "capability",
    [Capability.GRAPH_MINING, Capability.HYPOTHESIS_TESTING],
)
def test_data_explorer_dispatcher_rejects_other_specialist_capabilities(capability) -> None:
    class OtherSpecialist:
        async def run(
            self, input: DataExplorerInput, context: DataExplorerExecutionContext
        ):
            raise AssertionError("Other specialists must not cross the Data Explorer result seam.")

    registry = DataExplorerRegistry()
    registry.register_factory(capability, OtherSpecialist)

    with pytest.raises(ValueError, match="cannot invoke Graph Miner or Hypothesis Analyst"):
        asyncio.run(
            DataExplorerDispatcher(registry).dispatch(
                make_prepared_execution(capability.id),
                DataExplorerExecutionContext(),
            )
        )


def test_executor_package_has_no_global_or_cross_specialist_registry() -> None:
    import agents.executor as package
    import agents.executor.registry as registry_module

    assert not hasattr(package, "executor_registry")
    assert not hasattr(registry_module, "executor_registry")
    assert not hasattr(package, "ExecutorRegistry")
    assert not hasattr(package, "ExecutorDispatcher")
    assert not hasattr(package, "ExecutorInput")
    assert not hasattr(package, "ExecutorContext")


def test_executor_scientific_input_excludes_planner_and_retrieval_context() -> None:
    assert {
        "assumptions",
        "task_motivation",
        "retrieval_scores",
        "session_frame",
        "raw_chat",
        "planner_state",
    }.isdisjoint(DataExplorerInput.model_fields)


def test_graph_miner_remains_outside_data_explorer_registry() -> None:
    registry = DataExplorerRegistry()
    with pytest.raises(NotImplementedError):
        GraphMiner()
    with pytest.raises(KeyError, match="No executor registered"):
        registry.get(Capability.GRAPH_MINING.id)
