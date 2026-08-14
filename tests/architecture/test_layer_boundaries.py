from __future__ import annotations

import ast
import importlib
import inspect
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
        "cognieda.agents.data_explorer",
        "cognieda.agents.data_explorer.analysis",
        "cognieda.agents.data_explorer.tools",
    )
    violations = [
        f"{path.relative_to(PROJECT_ROOT)} imports {module}"
        for path, module in _imports(_python_files("agents/planner"))
        if module == "pandas" or module.startswith(forbidden[1:])
    ]

    assert violations == []


def test_planner_cognitive_core_does_not_import_deferred_scientific_authority() -> None:
    forbidden_symbols = {
        "EvidenceRequest",
        "GovernanceDecision",
        "Hypothesis",
        "InvestigationProtocol",
    }
    violations: list[str] = []
    for path in _python_files("agents/planner"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            imported = forbidden_symbols.intersection(alias.name for alias in node.names)
            if imported:
                violations.append(
                    f"{path.relative_to(PROJECT_ROOT)} imports {sorted(imported)}"
                )

    assert violations == []


def test_planner_has_no_session_frame_dependency_or_legacy_graph_surface() -> None:
    planner_files = tuple(_python_files("agents/planner"))
    violations = [
        str(path.relative_to(PROJECT_ROOT))
        for path in planner_files
        if "SessionFrame" in path.read_text(encoding="utf-8")
    ]

    from cognieda.agents.planner.agent import Planner
    from cognieda.agents.planner.context import PlannerContext
    from cognieda.agents.planner.types import PlannerOutput, PlannerResult

    signature = inspect.signature(Planner.run)
    assert violations == []
    assert "session_frame" not in signature.parameters
    assert signature.parameters["context"].default is inspect.Parameter.empty
    assert inspect.iscoroutinefunction(Planner.reload)
    assert "session_frame" not in PlannerContext.model_fields
    assert "session_frame" not in PlannerResult.model_fields
    assert "session_frame" not in PlannerOutput.model_fields

    planner_root = SOURCE_ROOT / "agents" / "planner"
    for obsolete in ("model.py", "graph.py", "nodes.py"):
        assert not (planner_root / obsolete).exists()


def test_planner_production_source_has_no_obsolete_cognitive_symbols() -> None:
    planner_root = SOURCE_ROOT / "agents" / "planner"
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in planner_root.rglob("*.py")
    )

    for obsolete in (
        "PlannerDecision",
        "PlannerAction",
        "PlannerModelInput",
        "PlannerAnswerInput",
        "PlannerResponseDraft",
        "selected_capability",
        "created_assumption",
        "created_objective",
        "created_task",
        "work_outcome",
        "understand_request",
        "prepare_results",
        "dispatch_work",
        "compose_response",
    ):
        assert obsolete not in source


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
        if (
            path.is_file()
            and path.suffix != ".py"
            and "__pycache__" not in path.parts
            and "instruction" not in path.parts
        )
    ]

    assert non_python == []


def test_data_explorer_has_no_dynamic_code_execution() -> None:
    locations = [
        path.relative_to(SOURCE_ROOT).as_posix()
        for path in _python_files("agents/data_explorer")
        if any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in {"exec", "eval"}
            for node in ast.walk(
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            )
        )
    ]

    assert locations == []


def test_data_explorer_does_not_author_or_persist_evidence() -> None:
    forbidden_modules = {
        "cognieda.infrastructure.persistence.repositories.evidence_repository",
    }
    forbidden_symbols = {"Evidence", "EvidenceRepository"}
    violations: list[str] = []
    for path in _python_files("agents/data_explorer"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module in forbidden_modules:
                    violations.append(f"{path.relative_to(PROJECT_ROOT)} imports {node.module}")
                imported = forbidden_symbols.intersection(alias.name for alias in node.names)
                if imported:
                    violations.append(
                        f"{path.relative_to(PROJECT_ROOT)} imports {sorted(imported)}"
                    )

    assert violations == []


def test_removed_unsafe_analysis_adapter_is_absent_and_unreferenced() -> None:
    data_explorer_root = SOURCE_ROOT / "agents" / "data_explorer"

    assert not (data_explorer_root / "tools" / "_unsafe_python_analysis.py").exists()
    assert all(
        "_unsafe_python_analysis" not in path.read_text(encoding="utf-8")
        for path in data_explorer_root.rglob("*.py")
    )


def test_execution_package_does_not_own_data_explorer_analysis_contracts() -> None:
    forbidden = {
        "CorrelationMethod",
        "DataAnalysisOperation",
        "DataAnalysisPlan",
        "DataExplorerInput",
        "DataProfile",
    }
    violations: list[str] = []
    for path in _python_files("execution"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in forbidden:
                violations.append(f"{path.relative_to(PROJECT_ROOT)} defines {node.name}")
            if isinstance(node, ast.ImportFrom):
                imported = forbidden.intersection(alias.name for alias in node.names)
                if imported:
                    violations.append(
                        f"{path.relative_to(PROJECT_ROOT)} imports {sorted(imported)}"
                    )

    assert violations == []


def test_planner_and_runtime_do_not_construct_data_analysis_plans() -> None:
    violations: list[str] = []
    for relative_root in ("agents/planner", "runtime"):
        for path in _python_files(relative_root):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    imported = {
                        alias.name for alias in node.names if alias.name == "DataAnalysisPlan"
                    }
                    if imported:
                        violations.append(
                            f"{path.relative_to(PROJECT_ROOT)} imports DataAnalysisPlan"
                        )
                if isinstance(node, ast.Name) and node.id == "DataAnalysisPlan":
                    violations.append(
                        f"{path.relative_to(PROJECT_ROOT)} references DataAnalysisPlan"
                    )

    assert violations == []


def test_data_explorer_is_persistence_free() -> None:
    violations = [
        f"{path.relative_to(PROJECT_ROOT)} imports {module}"
        for path, module in _imports(_python_files("agents/data_explorer"))
        if module.startswith("cognieda.infrastructure.persistence") or module == "sqlmodel"
    ]

    assert violations == []
