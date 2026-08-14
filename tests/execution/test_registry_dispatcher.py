from __future__ import annotations

import asyncio
import os
from uuid import uuid4

import pytest
from pydantic import ValidationError

from cognieda.delegation import (
    Capability,
    CapabilityNotRegisteredError,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    ExecutorContext,
    ExecutorDispatcher,
    ExecutorInput,
    ExecutorProviderError,
    ExecutorRegistry,
    normalize_for_planner,
)
from cognieda.delegation.capabilities import Capability as CapabilityFromOwner
from cognieda.runtime.bootstrap import bootstrap_application
from cognieda.schemas.artifacts import Task
from cognieda.schemas.enums import TaskKind


def _task() -> Task:
    return Task(
        objective_id=uuid4(),
        kind=TaskKind.DATA,
        instruction="Check whether the treatment increases the target metric.",
    )


def _request(capability: Capability = Capability.DATA_ANALYSIS) -> ExecutionRequest:
    return ExecutionRequest(
        capability=capability,
        input=ExecutorInput(task=_task()),
        context=ExecutorContext(),
    )


class FakeProvider:
    def __init__(self, dependency: str = "default") -> None:
        self.dependency = dependency
        self.calls: list[ExecutionRequest] = []

    async def run(self, request: ExecutionRequest) -> ExecutionResult:
        self.calls.append(request)
        return ExecutionResult(
            source_role="fake",
            task_id=request.input.task.task_id,
            work_id=f"fake:{request.input.task.task_id}",
            status=ExecutionStatus.SUCCEEDED,
        )


class FailingProvider:
    async def run(self, request: ExecutionRequest) -> ExecutionResult:
        raise RuntimeError("provider exploded")


class InvalidResultProvider:
    async def run(self, request: ExecutionRequest) -> object:
        return {"status": "succeeded"}


def test_capability_values_and_import_identity_are_stable() -> None:
    assert Capability is CapabilityFromOwner
    assert Capability.DATA_ANALYSIS.value == "data_analysis"
    assert Capability.DATA_PROFILING.value == "data_profiling"
    assert Capability.DATA_TRANSFORMATION.value == "data_transformation"


def test_execution_request_rejects_unknown_raw_capability() -> None:
    with pytest.raises(ValidationError):
        ExecutionRequest(
            capability="missing",
            input=ExecutorInput(task=_task()),
            context=ExecutorContext(),
        )


def test_registry_registers_one_capability() -> None:
    registry = ExecutorRegistry()
    registry.register_provider(FakeProvider, capabilities=(Capability.DATA_ANALYSIS,))

    assert isinstance(registry.resolve(Capability.DATA_ANALYSIS), FakeProvider)
    assert registry.list_capabilities() == (Capability.DATA_ANALYSIS,)


def test_registry_maps_multiple_capabilities_to_one_reused_provider() -> None:
    registry = ExecutorRegistry()
    registry.register_provider(
        FakeProvider,
        capabilities=(Capability.DATA_ANALYSIS, Capability.DATA_PROFILING),
    )

    first = registry.resolve(Capability.DATA_ANALYSIS)
    second = registry.resolve(Capability.DATA_PROFILING)

    assert first is second


def test_registry_rejects_empty_and_duplicate_registration() -> None:
    registry = ExecutorRegistry()
    with pytest.raises(ValueError, match="At least one capability"):
        registry.register_provider(FakeProvider, capabilities=())

    registry.register_provider(FakeProvider, capabilities=(Capability.DATA_ANALYSIS,))
    with pytest.raises(ValueError, match="Capability already registered: data_analysis"):
        registry.register_provider(FakeProvider, capabilities=(Capability.DATA_ANALYSIS,))


def test_registry_fails_closed_for_unregistered_capability() -> None:
    registry = ExecutorRegistry()
    with pytest.raises(CapabilityNotRegisteredError, match="graph_mining"):
        registry.resolve(Capability.GRAPH_MINING)


def test_dependency_aware_factory_constructs_provider_once() -> None:
    registry = ExecutorRegistry()
    dependency = "injected-repository"
    factory_calls = 0

    def factory() -> FakeProvider:
        nonlocal factory_calls
        factory_calls += 1
        return FakeProvider(dependency)

    registry.register_provider(
        factory,
        capabilities=(Capability.DATA_ANALYSIS, Capability.DATA_PROFILING),
    )

    provider = registry.resolve(Capability.DATA_ANALYSIS)
    assert registry.resolve(Capability.DATA_PROFILING) is provider
    assert provider.dependency == dependency
    assert factory_calls == 1


def test_dispatcher_invokes_registered_provider_asynchronously() -> None:
    registry = ExecutorRegistry()
    registry.register_provider(FakeProvider, capabilities=(Capability.DATA_ANALYSIS,))
    dispatcher = ExecutorDispatcher(registry)
    request = _request()

    result = asyncio.run(dispatcher.dispatch(request))
    provider = registry.resolve(Capability.DATA_ANALYSIS)

    assert result.status == ExecutionStatus.SUCCEEDED
    assert provider.calls == [request]


def test_dispatcher_preserves_controlled_provider_failure() -> None:
    registry = ExecutorRegistry()
    registry.register_provider(FailingProvider, capabilities=(Capability.DATA_ANALYSIS,))
    dispatcher = ExecutorDispatcher(registry)

    with pytest.raises(ExecutorProviderError, match="provider exploded") as error:
        asyncio.run(dispatcher.dispatch(_request()))

    assert isinstance(error.value.__cause__, RuntimeError)


def test_dispatcher_rejects_incompatible_provider_result() -> None:
    registry = ExecutorRegistry()
    registry.register_provider(
        InvalidResultProvider,
        capabilities=(Capability.DATA_ANALYSIS,),
    )

    with pytest.raises(ExecutorProviderError, match="incompatible result"):
        asyncio.run(ExecutorDispatcher(registry).dispatch(_request()))


def test_planner_projection_does_not_expose_role_native_fields() -> None:
    outcome = normalize_for_planner(
        ExecutionResult(
            source_role="fake",
            task_id=_task().task_id,
            work_id="fake:1",
            status=ExecutionStatus.SUCCEEDED,
        )
    )

    assert outcome.source_role == "fake"
    assert outcome.permitted_next_actions == ["review_result"]
    assert len(outcome.result_digest) == 64


def test_bootstrap_composes_real_dispatcher_and_data_provider(tmp_path) -> None:
    application = bootstrap_application(tmp_path)
    request = _request(Capability.DATA_TRANSFORMATION)

    result = asyncio.run(application.dispatcher.dispatch(request))

    assert result.status == ExecutionStatus.BLOCKED
    assert result.source_role == "data_explorer"


def test_bootstrap_creates_workspace_env_file(tmp_path) -> None:
    bootstrap_application(tmp_path)

    assert (tmp_path / ".env").is_file()


def test_bootstrap_loads_api_key_from_workspace_env(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    (tmp_path / ".env").write_text(
        "GOOGLE_API_KEY=example-google-key\n",
        encoding="utf-8",
    )

    application = bootstrap_application(tmp_path)

    assert os.environ.get("GOOGLE_API_KEY") == "example-google-key"
    assert application.workspace.project_config.resolve_model().api_key == "example-google-key"
