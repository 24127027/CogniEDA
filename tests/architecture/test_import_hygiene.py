from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

from cognieda.agents.data_explorer.analysis import DatasetProfiler
from cognieda.agents.planner.agent import Planner
from cognieda.cli.renderer import Renderer
from cognieda.db import create_db_engine
from cognieda.execution import Capability
from cognieda.execution.capabilities import Capability as CapabilityOwner
from cognieda.infrastructure.agent_tooling import AgentTooling
from cognieda.memory import SessionFrameBuilder
from cognieda.repositories import TaskRepository
from cognieda.runtime import Application
from cognieda.schemas import Task
from cognieda.schemas.artifacts import Task as TaskOwner

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LEGACY_IMPORT_ROOTS = frozenset(
    {
        "agents",
        "cli",
        "data",
        "db",
        "memory",
        "repositories",
        "runtime",
        "schemas",
        "src",
        "tools",
    }
)
REMOVED_ROOT_SHIMS = ("agents", "cli", "runtime", "schemas", "tools")


def _active_python_files() -> Iterator[Path]:
    roots = (
        PROJECT_ROOT / "src" / "cognieda",
        PROJECT_ROOT / "tests",
        PROJECT_ROOT / "scripts",
    )
    for root in roots:
        if root.exists():
            yield from root.rglob("*.py")
    yield from PROJECT_ROOT.glob("*.py")


def _legacy_import_root(node: ast.Import | ast.ImportFrom) -> str | None:
    if isinstance(node, ast.Import):
        for alias in node.names:
            root = alias.name.partition(".")[0]
            if root in LEGACY_IMPORT_ROOTS:
                return root
        return None
    if node.level or node.module is None:
        return None
    root = node.module.partition(".")[0]
    return root if root in LEGACY_IMPORT_ROOTS else None


def _is_sys_path_mutation(node: ast.Call) -> bool:
    function = node.func
    return (
        isinstance(function, ast.Attribute)
        and function.attr in {"append", "insert"}
        and isinstance(function.value, ast.Attribute)
        and function.value.attr == "path"
        and isinstance(function.value.value, ast.Name)
        and function.value.value.id == "sys"
    )


def test_active_python_uses_only_the_canonical_project_namespace() -> None:
    violations: list[str] = []
    for path in _active_python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        relative_path = path.relative_to(PROJECT_ROOT)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                root = _legacy_import_root(node)
                if root is not None:
                    violations.append(f"{relative_path}:{node.lineno}: legacy import root {root}")
            elif isinstance(node, ast.Call) and _is_sys_path_mutation(node):
                violations.append(f"{relative_path}:{node.lineno}: sys.path mutation")
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
                if any(
                    isinstance(target, ast.Name) and target.id == "__path__" for target in targets
                ):
                    violations.append(f"{relative_path}:{node.lineno}: __path__ redirection")

    assert violations == []


def test_legacy_root_shims_and_root_main_are_absent() -> None:
    for name in REMOVED_ROOT_SHIMS:
        assert not (PROJECT_ROOT / name).exists()
    assert not (PROJECT_ROOT / "data" / "__init__.py").exists()
    assert not (PROJECT_ROOT / "src" / "__init__.py").exists()
    assert not (PROJECT_ROOT / "main.py").exists()


def test_major_package_boundaries_import_from_cognieda() -> None:
    assert all(
        value is not None
        for value in (
            Planner,
            Renderer,
            DatasetProfiler,
            create_db_engine,
            SessionFrameBuilder,
            TaskRepository,
            Application,
            AgentTooling,
        )
    )


def test_public_exports_share_canonical_class_identity() -> None:
    assert Task is TaskOwner
    assert Capability is CapabilityOwner
