from __future__ import annotations

import asyncio
import importlib
from uuid import uuid4

import pytest
from pydantic import ValidationError

from agents.executor import (
    DataExplorerAdapter,
    DataExplorerDispatcher,
    DataExplorerExecutionContext,
    DataExplorerInput,
    DataExplorerRegistry,
)
from agents.executor.graph_miner.agent import GraphMiner
from agents.executor.hypothesis_analyst.agent import HypothesisAnalyst
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
    DataExplorerSuccessResult,
)

EXECUTOR_ID = "deterministic"


def make_prepared_execution(executor_id: str = EXECUTOR_ID) -> PreparedExecution:
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


class GraphBackedExecutor(DataExplorerAdapter):
    def __init__(self) -> None:
        self.fake_graph = FakeGraph()
        super().__init__(lambda: self.fake_graph)


class FakeExecutor(DataExplorerAdapter):
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


def test_registry_reuses_one_lazy_adapter_instance() -> None:
    FakeExecutor.instance_count = 0
    registry = DataExplorerRegistry()

    registry.register_factory(EXECUTOR_ID, FakeExecutor)

    first = registry.get(EXECUTOR_ID)
    second = registry.get(EXECUTOR_ID)

    assert first is second
    assert FakeExecutor.instance_count == 1


def test_registry_rejects_duplicate_capability() -> None:
    registry = DataExplorerRegistry()
    registry.register_factory(EXECUTOR_ID, FakeExecutor)

    with pytest.raises(ValueError, match="already has an explicit registration"):
        registry.register_factory(EXECUTOR_ID, FakeExecutor)
    with pytest.raises(ValueError, match="already has an explicit registration"):
        registry.register_factory("other-data-explorer", FakeExecutor)


@pytest.mark.parametrize("executor_id", ["graph_mining", "hypothesis_testing"])
def test_registry_rejects_separate_specialist_ids(executor_id: str) -> None:
    registry = DataExplorerRegistry()

    with pytest.raises(ValueError, match="separate specialist boundary"):
        registry.register_factory(executor_id, FakeExecutor)


def test_registry_reports_unknown_capability() -> None:
    registry = DataExplorerRegistry()

    with pytest.raises(KeyError, match="No Data Explorer registered for executor id: missing"):
        registry.get("missing")


def test_registry_lists_only_the_explicit_executor_id() -> None:
    registry = DataExplorerRegistry()

    registry.register_factory(EXECUTOR_ID, FakeExecutor)

    assert registry.list_executor_ids() == (EXECUTOR_ID,)


def test_dispatcher_invokes_registered_executor() -> None:
    registry = DataExplorerRegistry()
    registry.register_factory(EXECUTOR_ID, FakeExecutor)
    dispatcher = DataExplorerDispatcher(registry)
    executor = registry.get(EXECUTOR_ID)

    prepared = make_prepared_execution()
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

    registry.register_factory(EXECUTOR_ID, failing_factory)

    assert calls == 0
    with pytest.raises(RuntimeError, match="factory failed"):
        registry.get(EXECUTOR_ID)
    assert calls == 1


def test_registry_rejects_malformed_factory_result() -> None:
    registry = DataExplorerRegistry()
    registry.register_factory(EXECUTOR_ID, object)

    with pytest.raises(TypeError, match="async run method"):
        registry.get(EXECUTOR_ID)


@pytest.mark.parametrize(
    "module_order",
    [
        (
            "agents.executor.graph_miner.agent",
            "agents.executor.hypothesis_analyst.agent",
            "agents.executor.registry",
        ),
        (
            "agents.executor.registry",
            "agents.executor.hypothesis_analyst.agent",
            "agents.executor.graph_miner.agent",
        ),
    ],
)
def test_import_order_does_not_register_any_adapter(module_order: tuple[str, ...]) -> None:
    for module_name in module_order:
        importlib.import_module(module_name)

    assert DataExplorerRegistry().list_executor_ids() == ()


def test_planner_output_cannot_embed_an_executor_request() -> None:
    """Planner model output must flow through planner admission, not executor dispatch."""

    planner_fields = set(PlannerOutput.model_fields)

    assert "execution_request" not in planner_fields
    assert {"planner_operations", "executor_dispatch_ref"} <= planner_fields


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
    registry.register_factory(EXECUTOR_ID, MaliciousExecutor)

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        asyncio.run(
            DataExplorerDispatcher(registry).dispatch(
                make_prepared_execution(),
                DataExplorerExecutionContext(),
            )
        )


def test_dispatcher_propagates_adapter_invocation_failure() -> None:
    class FailingAdapter:
        async def run(
            self, input: DataExplorerInput, context: DataExplorerExecutionContext
        ) -> DataExplorerResult:
            raise RuntimeError("adapter failed")

    registry = DataExplorerRegistry()
    registry.register_factory(EXECUTOR_ID, FailingAdapter)

    with pytest.raises(RuntimeError, match="adapter failed"):
        asyncio.run(
            DataExplorerDispatcher(registry).dispatch(
                make_prepared_execution(),
                DataExplorerExecutionContext(),
            )
        )


def test_graph_miner_and_hypothesis_analyst_are_not_data_explorer_executors() -> None:
    assert not issubclass(GraphMiner, DataExplorerAdapter)
    assert not issubclass(HypothesisAnalyst, DataExplorerAdapter)


@pytest.mark.parametrize("executor_id", ["graph_mining", "hypothesis_testing"])
def test_data_explorer_dispatcher_rejects_unregistered_specialist_ids(
    executor_id: str,
) -> None:
    registry = DataExplorerRegistry()
    registry.register_factory(EXECUTOR_ID, FakeExecutor)

    with pytest.raises(KeyError, match="No Data Explorer registered"):
        asyncio.run(
            DataExplorerDispatcher(registry).dispatch(
                make_prepared_execution(executor_id),
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
    assert not hasattr(package, "DataExplorerExecutor")
    assert not hasattr(package, "GraphMinerExecutor")
    assert not hasattr(package, "HypothesisAnalystExecutor")


def test_executor_scientific_input_excludes_planner_and_retrieval_context() -> None:
    assert {
        "assumptions",
        "task_motivation",
        "retrieval_scores",
        "session_frame",
        "raw_chat",
        "planner_state",
    }.isdisjoint(DataExplorerInput.model_fields)
    prepared = make_prepared_execution()
    payload = {
        "execution_run_id": prepared.execution_run_id,
        "task_id": prepared.task_ref,
        "hypothesis_id": prepared.hypothesis_ref,
        "data_profile_id": prepared.data_profile_ref,
        "dataset_path": prepared.dataset_path,
        "hypothesis": prepared.hypothesis,
        "specification": prepared.specification,
        "assumptions": ["forbidden"],
    }
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        DataExplorerInput.model_validate(payload)


def test_data_explorer_result_excludes_identity_evaluation_and_persistence_authority() -> None:
    forbidden = {
        "execution_run_id",
        "evidence_id",
        "discovery_id",
        "evaluation",
        "epistemic_status",
        "discovery_proposal",
        "lifecycle_state",
        "persistence_commands",
    }

    assert forbidden.isdisjoint(DataExplorerSuccessResult.model_fields)
    assert forbidden.isdisjoint(DataExplorerFailureResult.model_fields)


def test_graph_miner_remains_outside_data_explorer_registry() -> None:
    registry = DataExplorerRegistry()
    with pytest.raises(NotImplementedError):
        GraphMiner()
    with pytest.raises(KeyError, match="No Data Explorer registered"):
        registry.get("graph_mining")
