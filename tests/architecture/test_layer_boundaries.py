from __future__ import annotations

import ast
import importlib
from collections.abc import Iterable
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = PROJECT_ROOT / "src" / "cognieda"


def _imports(paths: Iterable[Path]) -> list[tuple[Path, str]]:
    imports: list[tuple[Path, str]] = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend((path, alias.name) for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imports.append((path, node.module))
    return imports


def _python_files(relative_root: str) -> Iterable[Path]:
    yield from (SOURCE_ROOT / relative_root).rglob("*.py")


def test_planner_cannot_access_dataset_implementation_directly() -> None:
    forbidden = (
        "pandas",
        "cognieda.infrastructure.datasets",
        "cognieda.agents.data_explorer.analysis",
        "cognieda.agents.data_explorer.tools",
    )
    violations = [
        f"{path.relative_to(PROJECT_ROOT)} imports {module}"
        for path, module in _imports(_python_files("agents/planner"))
        if module == "pandas" or module.startswith(forbidden[1:])
    ]

    assert violations == []


def test_inward_layers_do_not_depend_on_cli() -> None:
    violations = [
        f"{path.relative_to(PROJECT_ROOT)} imports {module}"
        for layer in ("application", "execution", "schemas")
        for path, module in _imports(_python_files(layer))
        if module.startswith("cognieda.cli")
    ]

    assert violations == []


def test_removed_ownership_packages_have_no_python_source() -> None:
    removed = (
        "agents/executor",
        "data",
        "db",
        "memory",
        "repositories",
        "runtime/orchestrator",
        "tools",
    )

    assert {
        path
        for path in removed
        if any((SOURCE_ROOT / path).rglob("*.py"))
    } == set()


def test_specialist_roles_are_peer_packages() -> None:
    modules = (
        "cognieda.agents.planner.agent",
        "cognieda.agents.data_explorer",
        "cognieda.agents.hypothesis_analyst",
        "cognieda.agents.graph_miner",
    )

    assert all(importlib.import_module(module) is not None for module in modules)


def test_production_source_contains_only_python_files() -> None:
    non_python = [
        path.relative_to(PROJECT_ROOT)
        for path in SOURCE_ROOT.rglob("*")
        if path.is_file() and path.suffix != ".py" and "__pycache__" not in path.parts
    ]

    assert non_python == []


def test_dynamic_code_execution_is_confined_to_named_provisional_adapter() -> None:
    locations = [
        path.relative_to(SOURCE_ROOT).as_posix()
        for path in SOURCE_ROOT.rglob("*.py")
        if any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "exec"
            for node in ast.walk(
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            )
        )
    ]

    assert locations == [
        "agents/data_explorer/tools/_unsafe_python_analysis.py",
    ]
