from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = PROJECT_ROOT / "src" / "cognieda"


def test_product_repository_has_no_research_workspace_state() -> None:
    forbidden = ("data", "artifacts", ".dvc", ".dvcignore")

    assert [name for name in forbidden if (PROJECT_ROOT / name).exists()] == []


def test_production_source_does_not_resolve_package_relative_user_data() -> None:
    violations: list[Path] = []
    for path in SOURCE_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        strings = {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        if "__file__" in names and "data" in strings:
            violations.append(path.relative_to(PROJECT_ROOT))

    assert violations == []


def test_production_source_does_not_know_test_fixture_paths() -> None:
    violations = [
        path.relative_to(PROJECT_ROOT)
        for path in SOURCE_ROOT.rglob("*.py")
        if "tests/fixtures" in path.read_text(encoding="utf-8").replace("\\", "/")
    ]

    assert violations == []
