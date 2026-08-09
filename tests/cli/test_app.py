from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from cognieda.cli import app as cli_app


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
