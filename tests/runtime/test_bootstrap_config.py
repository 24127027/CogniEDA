from __future__ import annotations

import pytest

from cognieda.runtime.bootstrap import resolve_model_config
from cognieda.runtime.workspace import ProjectConfig, Workspace


def _workspace(tmp_path, values: dict[str, object]) -> Workspace:
    return Workspace(tmp_path, ProjectConfig(values=values))


def test_workspace_model_configuration_takes_precedence_over_environment(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("COGNIEDA_MODEL_NAME", "environment-model")
    monkeypatch.setenv("COGNIEDA_OPENAI_BASE_URL", "https://environment.example/v1")
    monkeypatch.setenv("COGNIEDA_OPENAI_API_KEY", "environment-key")
    workspace = _workspace(
        tmp_path,
        {
            "model": {
                "name": "workspace-model",
                "base_url": "https://workspace.example/v1",
                "api_key": "workspace-key",
            }
        },
    )

    config = resolve_model_config(workspace)

    assert config.model_name == "workspace-model"
    assert config.base_url == "https://workspace.example/v1"
    assert config.api_key == "workspace-key"


def test_environment_fills_missing_model_configuration(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("COGNIEDA_MODEL_NAME", "environment-model")
    monkeypatch.setenv("COGNIEDA_OPENAI_BASE_URL", "https://environment.example/v1")
    monkeypatch.setenv("COGNIEDA_OPENAI_API_KEY", "environment-key")

    config = resolve_model_config(_workspace(tmp_path, {}))

    assert config.model_name == "environment-model"
    assert config.base_url == "https://environment.example/v1"
    assert config.api_key == "environment-key"


def test_missing_required_model_configuration_fails_closed(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("COGNIEDA_MODEL_NAME", raising=False)
    monkeypatch.delenv("COGNIEDA_OPENAI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="Model name is required"):
        resolve_model_config(_workspace(tmp_path, {}))
