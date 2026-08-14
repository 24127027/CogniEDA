from __future__ import annotations

import pytest

from cognieda.runtime.workspace import MissingModelCredentialError, Workspace


@pytest.fixture(autouse=True)
def _clear_provider_keys(monkeypatch) -> None:
    for name in ("GOOGLE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)


def test_default_workspace_uses_canonical_google_profile(tmp_path) -> None:
    workspace = Workspace.open(tmp_path)

    assert workspace.project_config.default_provider == "google"
    assert workspace.project_config.providers["google"].type == "google"


@pytest.mark.parametrize(
    ("profile", "provider_type", "environment_name"),
    [
        ("google", "google", "GOOGLE_API_KEY"),
        ("openai", "openai", "OPENAI_API_KEY"),
        ("anthropic", "anthropic", "ANTHROPIC_API_KEY"),
    ],
)
def test_selected_profile_resolves_model_from_its_exact_environment_key(
    monkeypatch,
    tmp_path,
    profile: str,
    provider_type: str,
    environment_name: str,
) -> None:
    workspace = Workspace.open(tmp_path)
    workspace.use_provider(profile)
    monkeypatch.setenv(environment_name, "provider-key")

    config = workspace.project_config.resolve_model()

    assert config.provider == provider_type
    assert config.api_key == "provider-key"


def test_missing_selected_provider_key_fails_closed(tmp_path) -> None:
    workspace = Workspace.open(tmp_path)

    with pytest.raises(MissingModelCredentialError, match="GOOGLE_API_KEY"):
        workspace.project_config.resolve_model()


def test_unknown_selected_profile_fails_closed(tmp_path) -> None:
    workspace = Workspace.open(tmp_path)
    workspace.project_config.default_provider = "unsupported"

    with pytest.raises(ValueError, match="Unknown provider 'unsupported'"):
        workspace.project_config.resolve_model()
