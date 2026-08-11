from __future__ import annotations

import pytest

from cognieda.runtime.bootstrap import resolve_model_config
from cognieda.runtime.workspace import ProjectConfig, Workspace

_MODEL_ENVIRONMENT_NAMES = (
    "COGNIEDA_MODEL_PROVIDER",
    "COGNIEDA_MODEL_NAME",
    "MODEL_BASE_URL",
    "MODEL_API_KEY",
    "COGNIEDA_OPENAI_BASE_URL",
    "COGNIEDA_OPENAI_API_KEY",
)


@pytest.fixture(autouse=True)
def _clear_model_environment(monkeypatch) -> None:
    for name in _MODEL_ENVIRONMENT_NAMES:
        monkeypatch.delenv(name, raising=False)


def _workspace(tmp_path, values: dict[str, object]) -> Workspace:
    return Workspace(tmp_path, ProjectConfig(values=values))


@pytest.mark.parametrize(
    ("configured_provider", "canonical_provider"),
    [
        ("openai", "openai"),
        ("google", "google"),
        ("gemini", "google"),
        ("anthropic", "anthropic"),
    ],
)
def test_provider_input_resolves_to_canonical_identity(
    tmp_path,
    configured_provider: str,
    canonical_provider: str,
) -> None:
    workspace = _workspace(
        tmp_path,
        {
            "model": {
                "provider": configured_provider,
                "name": "workspace-model",
                "api_key": "workspace-key",
            }
        },
    )

    config = resolve_model_config(workspace)

    assert config.provider == canonical_provider


def test_workspace_model_configuration_takes_precedence_over_environment(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("COGNIEDA_MODEL_PROVIDER", "openai")
    monkeypatch.setenv("COGNIEDA_MODEL_NAME", "environment-model")
    monkeypatch.setenv("MODEL_BASE_URL", "https://generic.example/v1")
    monkeypatch.setenv("MODEL_API_KEY", "generic-key")
    monkeypatch.setenv("COGNIEDA_OPENAI_BASE_URL", "https://legacy.example/v1")
    monkeypatch.setenv("COGNIEDA_OPENAI_API_KEY", "legacy-key")
    workspace = _workspace(
        tmp_path,
        {
            "model": {
                "provider": "anthropic",
                "name": "workspace-model",
                "base_url": "https://workspace.example/v1",
                "api_key": "workspace-key",
            }
        },
    )

    config = resolve_model_config(workspace)

    assert config.provider == "anthropic"
    assert config.model_name == "workspace-model"
    assert config.base_url == "https://workspace.example/v1"
    assert config.api_key == "workspace-key"


def test_generic_environment_fills_missing_model_configuration(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("COGNIEDA_MODEL_PROVIDER", "google")
    monkeypatch.setenv("COGNIEDA_MODEL_NAME", "environment-model")
    monkeypatch.setenv("MODEL_BASE_URL", "https://generic.example/v1")
    monkeypatch.setenv("MODEL_API_KEY", "generic-key")

    config = resolve_model_config(_workspace(tmp_path, {}))

    assert config.provider == "google"
    assert config.model_name == "environment-model"
    assert config.base_url == "https://generic.example/v1"
    assert config.api_key == "generic-key"


def test_legacy_openai_environment_remains_a_fallback(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("COGNIEDA_MODEL_PROVIDER", "openai")
    monkeypatch.setenv("COGNIEDA_MODEL_NAME", "environment-model")
    monkeypatch.setenv("COGNIEDA_OPENAI_BASE_URL", "https://legacy.example/v1")
    monkeypatch.setenv("COGNIEDA_OPENAI_API_KEY", "legacy-key")

    config = resolve_model_config(_workspace(tmp_path, {}))

    assert config.base_url == "https://legacy.example/v1"
    assert config.api_key == "legacy-key"


def test_generic_environment_takes_precedence_over_legacy_fallback(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("COGNIEDA_MODEL_PROVIDER", "openai")
    monkeypatch.setenv("COGNIEDA_MODEL_NAME", "environment-model")
    monkeypatch.setenv("MODEL_BASE_URL", "https://generic.example/v1")
    monkeypatch.setenv("MODEL_API_KEY", "generic-key")
    monkeypatch.setenv("COGNIEDA_OPENAI_BASE_URL", "https://legacy.example/v1")
    monkeypatch.setenv("COGNIEDA_OPENAI_API_KEY", "legacy-key")

    config = resolve_model_config(_workspace(tmp_path, {}))

    assert config.base_url == "https://generic.example/v1"
    assert config.api_key == "generic-key"


def test_missing_provider_fails_closed(tmp_path) -> None:
    workspace = _workspace(
        tmp_path,
        {"model": {"name": "workspace-model", "api_key": "workspace-key"}},
    )

    with pytest.raises(ValueError, match="Model provider is required"):
        resolve_model_config(workspace)


def test_unsupported_provider_fails_closed(tmp_path) -> None:
    workspace = _workspace(
        tmp_path,
        {
            "model": {
                "provider": "unsupported",
                "name": "workspace-model",
                "api_key": "workspace-key",
            }
        },
    )

    with pytest.raises(ValueError, match="Unsupported model provider: unsupported"):
        resolve_model_config(workspace)


def test_missing_model_name_fails_closed(tmp_path) -> None:
    workspace = _workspace(
        tmp_path,
        {"model": {"provider": "openai", "api_key": "workspace-key"}},
    )

    with pytest.raises(ValueError, match="Model name is required"):
        resolve_model_config(workspace)


def test_missing_api_key_fails_closed(tmp_path) -> None:
    workspace = _workspace(
        tmp_path,
        {"model": {"provider": "openai", "name": "workspace-model"}},
    )

    with pytest.raises(ValueError, match="Model API key is required"):
        resolve_model_config(workspace)
