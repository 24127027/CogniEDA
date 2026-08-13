from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from cognieda.agents.utilities import instruction


def _instruction_dir(tmp_path: Path) -> Path:
    instruction_dir = tmp_path / "explicit-instructions"
    instruction_dir.mkdir()
    (instruction_dir / "agents.md").write_text("built-in base", encoding="utf-8")
    (instruction_dir / "decide.txt").write_text("operation last", encoding="utf-8")
    return instruction_dir


def test_assembly_uses_explicit_directory_and_deterministic_layer_order(
    tmp_path: Path,
) -> None:
    instruction_dir = _instruction_dir(tmp_path)

    assembled = instruction.assemble(
        instruction_dir,
        "decide.txt",
        workspace_instruction="workspace supplement",
    )

    assert assembled == ["built-in base", "workspace supplement", "operation last"]


def test_missing_optional_workspace_instruction_keeps_built_in_base(
    tmp_path: Path,
) -> None:
    instruction_dir = _instruction_dir(tmp_path)

    assert instruction.assemble(instruction_dir, "decide.txt") == [
        "built-in base",
        "operation last",
    ]


def test_missing_required_instruction_files_fail_closed(tmp_path: Path) -> None:
    instruction_dir = tmp_path / "missing"
    instruction_dir.mkdir()

    with pytest.raises(FileNotFoundError, match="Built-in agent instruction"):
        instruction.assemble(instruction_dir, "decide.txt")

    (instruction_dir / "agents.md").write_text("base", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="decide.txt"):
        instruction.assemble(instruction_dir, "decide.txt")


def test_instruction_assembly_has_no_call_stack_discovery() -> None:
    source = inspect.getsource(instruction.assemble)

    assert "inspect.stack" not in source
    assert "caller" not in source
