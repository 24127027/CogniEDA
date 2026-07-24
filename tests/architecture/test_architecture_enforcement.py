"""Static guardrails for the execution-attempt transition boundary."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SOURCE_ROOT = Path("src")
TRANSITION_OWNER = "src/application/orchestrator/transition_service.py"
VALIDITY_OWNER = "src/application/orchestrator/validity_propagation_service.py"
MODEL_DEFINITION = "src/db/models.py"
EXECUTION_RECORDS = {
    "ExecutionRunRecord",
    "ExecutionInboxRecord",
    "ExecutionOutboxRecord",
}
AUTHORITATIVE_FIELDS = {
    "status",
    "attempt_version",
    "dispatch_idempotency_key",
    "worker_id",
    "lease_epoch",
    "lease_acquired_at",
    "lease_expires_at",
    "finalizer_owner_id",
    "finalization_fencing_epoch",
    "finalization_claimed_at",
    "finalization_expires_at",
    "serialized_observations",
    "result_digest",
    "method_id",
    "parameter_hash",
    "executor_type",
}
EXECUTION_REPOSITORIES = {
    "src/repositories/execution_run_repository.py",
    "src/repositories/execution_outbox_repository.py",
    "src/repositories/execution_inbox_repository.py",
}


def _called_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _imports_execution_records(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "db.models":
            if any(alias.name in EXECUTION_RECORDS for alias in node.names):
                return True
    return False


MIGRATION_OWNER = "src/db/legacy_migration.py"


def _violations(source: str, path: str) -> list[str]:
    """Return forbidden execution-record writes outside the transition owner."""
    if path in {TRANSITION_OWNER, VALIDITY_OWNER, MODEL_DEFINITION, MIGRATION_OWNER}:
        return []

    tree = ast.parse(source)
    violations: list[str] = []
    imports_execution_records = _imports_execution_records(tree)

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            called_name = _called_name(node)
            if called_name in EXECUTION_RECORDS:
                violations.append(f"execution record construction: {called_name}")
            if (
                called_name == "update"
                and node.args
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id in EXECUTION_RECORDS
            ):
                violations.append(f"execution record bulk update: {node.args[0].id}")

        if imports_execution_records and isinstance(
            node, (ast.Assign, ast.AnnAssign, ast.AugAssign)
        ):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id in {"run", "execution_run", "inbox", "outbox", "record"}
                    and target.attr in AUTHORITATIVE_FIELDS
                ):
                    violations.append(f"authoritative field assignment: {target.attr}")

    return violations


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "from db.models import ExecutionRunRecord\nExecutionRunRecord()\n",
            "execution record construction",
        ),
        (
            "from db.models import ExecutionRunRecord\nrun.status = 'completed'\n",
            "authoritative field assignment",
        ),
        (
            "from sqlalchemy import update\nfrom db.models import ExecutionInboxRecord\n"
            "update(ExecutionInboxRecord).values(status='processed')\n",
            "execution record bulk update",
        ),
    ],
)
def test_execution_boundary_detector_rejects_synthetic_bypasses(source: str, expected: str) -> None:
    violations = _violations(source, "src/application/orchestrator/forbidden.py")
    assert any(expected in violation for violation in violations)


def test_execution_repositories_do_not_expose_generic_mutators() -> None:
    """Read repositories may not become alternative lifecycle writers."""
    forbidden = {"create", "stage_create", "update", "save"}
    for repository_path in EXECUTION_REPOSITORIES:
        tree = ast.parse(Path(repository_path).read_text())
        public_methods = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
        }
        assert not public_methods & forbidden, (
            f"{repository_path} exposes a transition bypass: {sorted(public_methods & forbidden)}"
        )


def test_production_execution_record_writes_are_owned_by_transition_service() -> None:
    """Execution and validity transitions remain confined to their two owners."""
    violations: dict[str, list[str]] = {}
    for path in SOURCE_ROOT.rglob("*.py"):
        path_text = path.as_posix()
        found = _violations(path.read_text(), path_text)
        if found:
            violations[path_text] = found

    assert not violations, f"Execution transition boundary bypasses: {violations}"


def test_legacy_scientific_processing_is_unreachable_in_src() -> None:
    """Legacy scientific processing may not be imported or called by active execution paths."""
    unreachable_module = "application.orchestrator.scientific_processing"
    legacy_file = "src/application/orchestrator/scientific_processing.py"

    violations: list[str] = []
    for path in SOURCE_ROOT.rglob("*.py"):
        path_text = path.as_posix()
        if path_text == legacy_file:
            continue

        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == unreachable_module:
                violations.append(f"{path_text}: imports from {unreachable_module}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == unreachable_module:
                        violations.append(f"{path_text}: imports {unreachable_module}")

    assert not violations, (
        f"Legacy scientific processing is reachable from active paths: {violations}"
    )


def test_discovery_admission_sole_writer_enforcement() -> None:
    """EvaluationControl COMMITTED state is written only by AtomicDiscoveryAdmissionService."""
    allowed_writer = "src/application/orchestrator/atomic_discovery_admission.py"

    violations: list[str] = []
    for path in SOURCE_ROOT.rglob("*.py"):
        path_text = path.as_posix()
        if path_text == allowed_writer:
            continue

        source = path.read_text()
        if (
            "state=EvaluationControlState.COMMITTED" in source
            or "state = EvaluationControlState.COMMITTED" in source
        ):
            violations.append(f"{path_text}: writes EvaluationControlState.COMMITTED")

    assert not violations, (
        f"EvaluationControlState.COMMITTED written outside atomic admission service: {violations}"
    )


def test_discovery_insert_and_private_stage_are_confined_to_cutover_boundary() -> None:
    """No production module may construct or stage a Discovery through another path."""

    stage_owner = "src/application/orchestrator/atomic_discovery_admission.py"
    storage_owner = "src/repositories/discovery_repository.py"
    allowed_constructors = {MODEL_DEFINITION, storage_owner}
    violations: list[str] = []

    for path in SOURCE_ROOT.rglob("*.py"):
        path_text = path.as_posix()
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            called_name = _called_name(node)
            if called_name == "DiscoveryRecord" and path_text not in allowed_constructors:
                violations.append(f"{path_text}: constructs DiscoveryRecord")
            if called_name == "_stage_create_from_atomic_admission" and path_text != stage_owner:
                violations.append(f"{path_text}: calls private Discovery stage")
    assert not violations, f"Discovery writer boundary bypasses: {violations}"


def test_discovery_repository_public_create_is_a_hard_failure() -> None:
    """The retained compatibility symbol cannot persist a Discovery."""

    tree = ast.parse(Path("src/repositories/discovery_repository.py").read_text())
    create_method = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "create"
    )
    assert any(
        isinstance(node, ast.Raise)
        and isinstance(node.exc, ast.Call)
        and _called_name(node.exc) == "RuntimeError"
        for node in ast.walk(create_method)
    )
    public_or_legacy_stage_methods = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "stage_create"
    }
    assert public_or_legacy_stage_methods == set()


def test_package6_removed_compatibility_modules_are_absent_and_unreferenced() -> None:
    """Deleted scientific-authority bridges cannot be imported by production."""

    forbidden = {
        "legacy_scientific_result_bridge",
        "legacy_compatibility",
        "scientific_processing",
        "process_scientific_result",
    }
    violations: list[str] = []
    for path in SOURCE_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        matches = sorted(token for token in forbidden if token in source)
        if matches:
            violations.append(f"{path.as_posix()}: {matches}")
    assert not violations, f"Removed compatibility path remains active: {violations}"


def test_evidence_writer_and_terminal_lifecycle_writers_are_sealed() -> None:
    """Generic repositories cannot bypass the two atomic admission transactions."""

    evidence_source = Path("src/repositories/evidence_repository.py").read_text(encoding="utf-8")
    hypothesis_source = Path("src/repositories/hypothesis_repository.py").read_text(
        encoding="utf-8"
    )
    task_source = Path("src/repositories/task_repository.py").read_text(encoding="utf-8")
    assert "Evidence creation is owned by the Evidence admission transaction." in (evidence_source)
    assert "Hypothesis EVALUATED transition is owned by" in hypothesis_source
    assert "Analytical Task COMPLETED transition is owned by" in task_source


def test_production_has_no_test_model_or_graph_miner_registration() -> None:
    """Deployment composition must supply real adapters and register Data Explorer only."""

    violations: list[str] = []
    for path in SOURCE_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        if "TestModel" in source:
            violations.append(f"{path.as_posix()}: TestModel")
        if (
            "register_factory(Capability.GRAPH_MINING" in source
            or "register(Capability.GRAPH_MINING" in source
        ):
            violations.append(f"{path.as_posix()}: Graph Miner registration")
    assert not violations, f"Production bootstrap bypasses: {violations}"


def test_supported_package_has_no_cli_surface() -> None:
    """Gate 0 must not package a command, placeholder entry point, or CLI module."""

    project = Path("pyproject.toml").read_text(encoding="utf-8")
    assert "[project.scripts]" not in project
    assert "console_scripts" not in project
    assert 'py-modules = ["main"]' not in project
    assert not Path("main.py").exists()
    assert not Path("src/cli").exists()
