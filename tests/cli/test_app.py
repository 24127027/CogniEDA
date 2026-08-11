from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from cognieda.cli import app as cli_app
from cognieda.runtime.bootstrap import resolve_model_config
from cognieda.runtime.workspace import Workspace


def test_help_exits_before_application_bootstrap(monkeypatch, capsys) -> None:
    bootstrap = Mock(side_effect=AssertionError("bootstrap must not run for --help"))
    monkeypatch.setattr(cli_app, "bootstrap_application", bootstrap)

    with pytest.raises(SystemExit) as exc_info:
        cli_app.main(["--help"])

    assert exc_info.value.code == 0
    assert "CogniEDA CLI" in capsys.readouterr().out
    bootstrap.assert_not_called()


def test_default_workspace_is_current_directory(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    args = cli_app.parse_args([])

    assert args.path == tmp_path


def test_main_forwards_selected_workspace_to_shared_repl(monkeypatch, tmp_path: Path) -> None:
    app = object()
    renderer = object()
    bootstrap = Mock(return_value=app)
    renderer_factory = Mock(return_value=renderer)
    seen: list[tuple[object, object]] = []

    async def fake_repl(received_app: object, received_renderer: object) -> None:
        seen.append((received_app, received_renderer))

    monkeypatch.setattr(cli_app, "bootstrap_application", bootstrap)
    monkeypatch.setattr(cli_app, "Renderer", renderer_factory)
    monkeypatch.setattr(cli_app, "repl", fake_repl)

    cli_app.main([str(tmp_path)])

    bootstrap.assert_called_once_with(tmp_path)
    renderer_factory.assert_called_once_with()
    assert seen == [(app, renderer)]


def test_main_loads_selected_workspace_env_without_overriding_process_values(
    monkeypatch, tmp_path: Path
) -> None:
    app = object()
    dotenv_loader = Mock()

    async def fake_repl(*_args: object) -> None:
        return None

    monkeypatch.setattr(cli_app, "load_dotenv", dotenv_loader)
    monkeypatch.setattr(cli_app, "bootstrap_application", Mock(return_value=app))
    monkeypatch.setattr(cli_app, "Renderer", Mock(return_value=object()))
    monkeypatch.setattr(cli_app, "repl", fake_repl)

    cli_app.main([str(tmp_path)])

    dotenv_loader.assert_called_once_with(
        dotenv_path=tmp_path.resolve() / ".env",
        override=False,
    )


def test_workspace_env_configures_a_new_workspace(monkeypatch, tmp_path: Path) -> None:
    for name in ("COGNIEDA_MODEL_PROVIDER", "COGNIEDA_MODEL_NAME", "MODEL_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    config_dir = tmp_path / ".cognieda"
    config_dir.mkdir()
    (config_dir / "project.toml").write_text(
        '[model]\nname = "workspace-model"\napi_key = "workspace-key"\n',
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text(
        "COGNIEDA_MODEL_PROVIDER=google\n"
        "COGNIEDA_MODEL_NAME=gemini-2.5-flash\n"
        "MODEL_API_KEY=example-key\n",
        encoding="utf-8",
    )

    cli_app.load_workspace_environment(tmp_path)
    config = resolve_model_config(Workspace.open(tmp_path))

    assert config.provider == "google"
    assert config.model_name == "workspace-model"
    assert config.api_key == "workspace-key"
