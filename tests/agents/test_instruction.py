from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest

from cognieda.agents.utilities import instruction


def _caller_tree(tmp_path: Path) -> tuple[Path, Path]:
    caller = tmp_path / "agent_role" / "agent.py"
    instruction_dir = caller.parent / "instruction"
    instruction_dir.mkdir(parents=True)
    caller.touch()
    (instruction_dir / "agents.md").write_text("built-in base", encoding="utf-8")
    (instruction_dir / "decide.txt").write_text("operation last", encoding="utf-8")
    return caller, instruction_dir


def _direct_caller(monkeypatch: pytest.MonkeyPatch, caller: Path) -> None:
    monkeypatch.setattr(
        instruction.inspect,
        "stack",
        lambda: [SimpleNamespace(filename=__file__), SimpleNamespace(filename=str(caller))],
    )


def test_assembly_resolves_direct_caller_sibling_and_orders_layers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    caller, _ = _caller_tree(tmp_path)
    _direct_caller(monkeypatch, caller)

    assembled = instruction.assemble(
        "decide.txt",
        workspace_instruction="workspace supplement",
    )

    assert assembled == ["built-in base", "workspace supplement", "operation last"]


def test_missing_optional_workspace_instruction_keeps_built_in_base(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    caller, _ = _caller_tree(tmp_path)
    _direct_caller(monkeypatch, caller)

    assert instruction.assemble("decide.txt") == ["built-in base", "operation last"]


def test_missing_required_instruction_files_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    caller = tmp_path / "agent_role" / "agent.py"
    (caller.parent / "instruction").mkdir(parents=True)
    caller.touch()
    _direct_caller(monkeypatch, caller)

    with pytest.raises(FileNotFoundError, match="Built-in agent instruction"):
        instruction.assemble("decide.txt")

    (caller.parent / "instruction" / "agents.md").write_text("base", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="decide.txt"):
        instruction.assemble("decide.txt")


def test_root_agents_md_is_not_loaded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "AGENTS.md").write_text("root instructions", encoding="utf-8")
    caller, _ = _caller_tree(tmp_path)
    _direct_caller(monkeypatch, caller)

    assembled = instruction.assemble("decide.txt")

    assert "root instructions" not in assembled


def test_instruction_assembly_documents_inspect_based_direct_caller_convention() -> None:
    source = inspect.getsource(instruction.assemble)

    assert "inspect.stack()[1]" in source
    assert 'caller_path.parent / "instruction"' in source
