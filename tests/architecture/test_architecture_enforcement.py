"""Static guardrails for the execution-attempt transition boundary."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SOURCE_ROOT = Path("src")
TRANSITION_OWNER = "src/application/orchestrator/transition_service.py"
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


def _violations(source: str, path: str) -> list[str]:
    """Return forbidden execution-record writes outside the transition owner."""
    if path in {TRANSITION_OWNER, MODEL_DEFINITION}:
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
    """The source-wide allowlist contains only ORM definitions and the owner."""
    violations: dict[str, list[str]] = {}
    for path in SOURCE_ROOT.rglob("*.py"):
        path_text = path.as_posix()
        found = _violations(path.read_text(), path_text)
        if found:
            violations[path_text] = found

    assert not violations, f"Execution transition boundary bypasses: {violations}"
