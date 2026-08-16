from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from cognieda.cli import app as cli_app
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


def test_parse_args_defaults_to_real_mode(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    args = cli_app.parse_args([])

    assert args.mode == "real"


def test_parse_args_accepts_mock_mode(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    args = cli_app.parse_args(["--mode", "mock"])

    assert args.mode == "mock"


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


def test_main_runs_mock_repl_without_bootstrap_in_mock_mode(
    monkeypatch, tmp_path: Path
) -> None:
    bootstrap = Mock(side_effect=AssertionError("bootstrap must not run in mock mode"))
    seen: list[tuple[object, object]] = []

    async def fake_repl(received_app: object, received_renderer: object) -> None:
        seen.append((received_app, received_renderer))

    monkeypatch.setattr(cli_app, "bootstrap_application", bootstrap)
    monkeypatch.setattr(cli_app, "repl", fake_repl)
    monkeypatch.setattr(cli_app, "Renderer", Mock(return_value=object()))

    cli_app.main(["--mode", "mock", str(tmp_path)])

    assert len(seen) == 1
    bootstrap.assert_not_called()


def test_main_loads_selected_workspace_env_without_overriding_process_values(
    monkeypatch, tmp_path: Path
) -> None:
    import cognieda.runtime.bootstrap as bootstrap_mod

    dotenv_loader = Mock()
    monkeypatch.setattr(bootstrap_mod, "load_dotenv", dotenv_loader)

    bootstrap_mod._load_workspace_environment(tmp_path)

    dotenv_loader.assert_called_once_with(
        dotenv_path=tmp_path.resolve() / ".env",
        override=False,
    )


def test_workspace_env_configures_a_new_workspace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from cognieda.runtime.bootstrap import _load_workspace_environment

    for name in ("GOOGLE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    workspace = Workspace.open(tmp_path)
    (tmp_path / ".env").write_text(
        "GOOGLE_API_KEY=example-google-key\n",
        encoding="utf-8",
    )

    _load_workspace_environment(tmp_path)
    config = workspace.project_config.resolve_model()

    assert config.provider == "google"
    assert config.model_name == "gemini-2.5-flash"
    assert config.api_key == "example-google-key"


