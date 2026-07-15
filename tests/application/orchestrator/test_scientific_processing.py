"""Unit tests for the standalone scientific finalization processing module."""

import ast
from pathlib import Path

import pytest


def test_finalizer_does_not_import_planner_nodes() -> None:
    """Verify architectural boundary: Finalization MUST NOT depend on the Planner control plane."""
    # Find the finalizer.py file
    src_dir = Path(__file__).parent.parent.parent.parent / "src"
    finalizer_path = src_dir / "application" / "orchestrator" / "finalizer.py"

    assert finalizer_path.exists()

    content = finalizer_path.read_text(encoding="utf-8")
    tree = ast.parse(content)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                assert not name.name.startswith("agents.planner.nodes"), (
                    f"finalizer.py imports {name.name}, violating architectural boundaries."
                )
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("agents.planner.nodes"):
                pytest.fail(
                    f"finalizer.py imports from {node.module}, violating architectural boundaries."
                )


@pytest.mark.parametrize(
    "module_name",
    ["finalizer.py", "scientific_processing.py", "execution_contracts.py"],
)
def test_scientific_finalization_modules_do_not_import_planner_types(module_name: str) -> None:
    """The durable scientific path must not depend on Planner graph contracts."""

    src_dir = Path(__file__).parent.parent.parent.parent / "src"
    tree = ast.parse((src_dir / "application" / "orchestrator" / module_name).read_text("utf-8"))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(not name.name.startswith("agents.planner") for name in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.module is None or not node.module.startswith("agents.planner")


def test_planner_nodes_do_not_construct_scientific_provenance_or_knowledge() -> None:
    """Planner control-flow code may admit contracts but cannot author scientific objects."""

    src_dir = Path(__file__).parent.parent.parent.parent / "src"
    tree = ast.parse((src_dir / "agents" / "planner" / "nodes.py").read_text("utf-8"))
    prohibited_constructors = {"AnalysisFrame", "ExecutionRun", "Evidence", "Discovery"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in prohibited_constructors
