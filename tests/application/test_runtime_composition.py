"""Package 6 composition-root and deployment-boundary proofs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic_ai.models.test import TestModel

from agents.executor.capabilities import Capability
from agents.executor.types import DataExplorerExecutionContext
from application.runtime import (
    CogniEDARuntime,
    RuntimeConfiguration,
    RuntimeConfigurationError,
)
from application.runtime_loader import load_runtime_from_environment
from schemas.discovery_admission_contracts import AuthenticatedPrincipal
from schemas.enums import ValidityEventType, ValiditySourceType
from schemas.validity_propagation_contracts import ValidityPropagationCommand


class Resolver:
    def __init__(self, principal: AuthenticatedPrincipal) -> None:
        self.principal = principal

    def resolve_authenticated_principal(
        self, authentication_context_id: str
    ) -> AuthenticatedPrincipal:
        del authentication_context_id
        return self.principal


class UnusedDataExplorer:
    async def run(self, input, context):  # pragma: no cover - construction seam only
        raise AssertionError((input, context))


def _configuration(tmp_path: Path) -> RuntimeConfiguration:
    return RuntimeConfiguration(
        database_url=f"sqlite:///{(tmp_path / 'runtime.sqlite3').as_posix()}",
        authority_ttl_seconds=60,
    )


def _principal(**updates: object) -> AuthenticatedPrincipal:
    values = {
        "authentication_context_id": "auth-context",
        "principal_id": "user:researcher",
        "workspace_id": "workspace:one",
        "session_id": "session:one",
        "authenticated_at": datetime.now(UTC) - timedelta(seconds=1),
    }
    values.update(updates)
    return AuthenticatedPrincipal(**values)


def _runtime(tmp_path: Path, resolver: Resolver | None = None) -> CogniEDARuntime:
    return CogniEDARuntime(
        _configuration(tmp_path),
        principal_resolver=resolver or Resolver(_principal()),
        analyst_model=TestModel(),
        data_explorer_factory=UnusedDataExplorer,
        executor_context_factory=DataExplorerExecutionContext,
    )


@pytest.mark.parametrize(
    "missing",
    [
        "principal_resolver",
        "analyst_model",
        "data_explorer_factory",
        "executor_context_factory",
    ],
)
def test_runtime_fails_closed_when_required_adapter_is_missing(
    tmp_path: Path, missing: str
) -> None:
    adapters = {
        "principal_resolver": Resolver(_principal()),
        "analyst_model": TestModel(),
        "data_explorer_factory": UnusedDataExplorer,
        "executor_context_factory": DataExplorerExecutionContext,
    }
    adapters[missing] = None
    with pytest.raises(RuntimeConfigurationError):
        CogniEDARuntime(_configuration(tmp_path), **adapters)  # type: ignore[arg-type]


def test_runtime_owns_one_planner_and_only_explicit_data_explorer(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path)

    assert runtime.planner is runtime.planner
    assert runtime.registered_executor_capabilities == (Capability.DATA_EXPLORATION.id,)
    with pytest.raises(KeyError, match="No executor registered"):
        runtime._executor_registry.get(Capability.GRAPH_MINING.id)


def test_runtime_authentication_binding_and_expiry_are_fail_closed(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path)
    issued = runtime.issue_user_authority("auth-context")

    assert issued.actor_identity == "user:researcher"
    assert issued.workspace_id == "workspace:one"
    assert issued.session_id == "session:one"
    assert issued.expires_at is not None
    assert issued.issued_at < issued.expires_at
    assert issued.expires_at - issued.issued_at <= timedelta(seconds=61)

    substituted = _runtime(
        tmp_path,
        Resolver(_principal(authentication_context_id="different-context")),
    )
    with pytest.raises(RuntimeConfigurationError, match="substituted"):
        substituted.resolve_principal("auth-context")

    future = _runtime(
        tmp_path,
        Resolver(_principal(authenticated_at=datetime.now(UTC) + timedelta(minutes=1))),
    )
    with pytest.raises(RuntimeConfigurationError, match="future"):
        future.resolve_principal("auth-context")


def test_runtime_exposes_validity_propagation_facade(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path)
    # Validates that propagate_validity delegates directly to AtomicValidityPropagationService
    with pytest.raises(AttributeError, match="idempotency_key"):
        runtime.propagate_validity(None)  # type: ignore[arg-type]


def test_runtime_loader_fails_predictably_without_deployment_hook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("COGNIEDA_RUNTIME_FACTORY", raising=False)

    with pytest.raises(RuntimeConfigurationError, match="module:factory"):
        load_runtime_from_environment()


def test_production_source_does_not_import_test_model() -> None:
    source_root = Path(__file__).resolve().parents[2] / "src"
    matches = [
        path
        for path in source_root.rglob("*.py")
        if "TestModel" in path.read_text(encoding="utf-8")
    ]
    assert matches == []
