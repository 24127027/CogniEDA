"""Static guardrails for the execution-attempt transition boundary."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SOURCE_ROOT = Path("src")
TRANSITION_OWNER = "src/application/execution/transition_service.py"
VALIDITY_OWNER = "src/application/validity/propagation_service.py"
MODEL_DEFINITION = "src/db/models/__init__.py"
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
    "src/repositories/execution/run.py",
    "src/repositories/execution/outbox.py",
    "src/repositories/execution/inbox.py",
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
    allowed = {
        Path(p).as_posix()
        for p in (TRANSITION_OWNER, VALIDITY_OWNER, MODEL_DEFINITION, MIGRATION_OWNER)
    }
    if Path(path).as_posix() in allowed:
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
    allowed_writer = "src/application/discovery/admission_service.py"

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

    stage_owner = "src/application/discovery/admission_service.py"
    storage_owner = "src/repositories/discovery/discovery.py"
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
    """The retained repository symbol cannot persist a Discovery."""

    tree = ast.parse(Path("src/repositories/discovery/discovery.py").read_text())
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
    """Generic repositories cannot bypass the atomic admission transactions."""

    evidence_source = Path("src/repositories/evidence/evidence.py").read_text(encoding="utf-8")
    hypothesis_source = Path("src/repositories/research/hypothesis.py").read_text(
        encoding="utf-8"
    )
    task_source = Path("src/repositories/research/task.py").read_text(encoding="utf-8")
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


def test_package_s1a_generic_executor_symbols_are_absent_from_active_code() -> None:
    """Active production code must use canonical DataExplorer names without generic aliases."""

    forbidden_symbols = {
        "DataExplorerExecutor",
        "ExecutorRegistry",
        "ExecutorDispatcher",
        "ExecutorInput",
        "ExecutorContext",
        "GraphMinerExecutor",
        "HypothesisAnalystExecutor",
    }
    violations: list[str] = []
    for path in SOURCE_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                if node.name in forbidden_symbols:
                    violations.append(f"{path.as_posix()}: defines {node.name}")
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in forbidden_symbols or alias.asname in forbidden_symbols:
                        violations.append(
                            f"{path.as_posix()}: imports {alias.name} (as {alias.asname})"
                        )
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in forbidden_symbols:
                        violations.append(f"{path.as_posix()}: assigns to {target.id}")

    assert not violations, f"Forbidden generic executor symbols found in src: {violations}"


def test_package_s1a_registry_has_no_decorator_or_cross_specialist_catalog() -> None:
    """The Data Explorer registry is explicit, singular, and role-specific."""

    registry_path = Path("src/agents/executor/registry.py")
    tree = ast.parse(registry_path.read_text(encoding="utf-8"))
    registry_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "DataExplorerRegistry"
    )
    method_names = {
        node.name for node in registry_class.body if isinstance(node, ast.FunctionDef)
    }
    assert "register" not in method_names
    assert "register_factory" in method_names
    assert not Path("src/agents/executor/capabilities.py").exists()

    source = registry_path.read_text(encoding="utf-8")
    assert "GraphMiner" not in source
    assert "HypothesisAnalyst" not in source
    assert "CapabilitySpec" not in source


def test_package_s1a_specialists_have_no_compatibility_executor_surface() -> None:
    """Graph Miner and Analyst stay outside Data Explorer invocation contracts."""

    assert not Path("src/agents/executor/graph_miner/state.py").exists()
    assert not Path("src/agents/executor/hypothesis_analyst/state.py").exists()
    assert not Path("src/agents/executor/hypothesis_analyst/graph.py").exists()

    package_source = Path("src/agents/executor/__init__.py").read_text(encoding="utf-8")
    assert "graph_miner" not in package_source
    assert "hypothesis_analyst" not in package_source


def test_package_s1b_execution_and_evidence_modules_moved_out_of_orchestrator() -> None:
    """Old execution/Evidence files must not exist in application.orchestrator."""

    forbidden_old_files = [
        "src/application/orchestrator/cancellation.py",
        "src/application/orchestrator/dispatcher.py",
        "src/application/orchestrator/execution_admission.py",
        "src/application/orchestrator/execution_contracts.py",
        "src/application/orchestrator/execution_identity.py",
        "src/application/orchestrator/finalizer.py",
        "src/application/orchestrator/receiver.py",
        "src/application/orchestrator/reconciler.py",
        "src/application/orchestrator/transition_service.py",
        "src/application/orchestrator/evidence_admission.py",
        "src/application/evidence/identity.py",
        "src/schemas/execution_observations.py",
        "src/schemas/data_explorer_contracts.py",
    ]
    present = [path for path in forbidden_old_files if Path(path).exists()]
    assert not present, f"Moved S1-B modules still exist in old paths: {present}"


def test_package_s1b_schemas_do_not_import_application() -> None:
    """Schemas must be self-contained value objects and not depend on application layer."""

    schemas_dir = Path("src/schemas")
    violations: list[str] = []
    for path in schemas_dir.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.startswith("application")
            ):
                violations.append(f"{path.as_posix()}: imports from {node.module}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("application"):
                        violations.append(f"{path.as_posix()}: imports {alias.name}")

    assert not violations, f"Schemas import application layer: {violations}"


def test_package_s1b_repositories_do_not_import_application() -> None:
    """Repositories must not import application layer logic or services."""

    repos_dir = Path("src/repositories")
    violations: list[str] = []
    for path in repos_dir.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.startswith("application")
            ):
                violations.append(f"{path.as_posix()}: imports from {node.module}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("application"):
                        violations.append(f"{path.as_posix()}: imports {alias.name}")

    assert not violations, f"Repositories import application layer: {violations}"


def test_package_s1b_no_old_orchestrator_import_paths_remain() -> None:
    """Active production code and tests must not import deleted old orchestrator paths."""

    forbidden_imports = [
        "application.orchestrator.cancellation",
        "application.orchestrator.dispatcher",
        "application.orchestrator.execution_admission",
        "application.orchestrator.execution_contracts",
        "application.orchestrator.execution_identity",
        "application.orchestrator.finalizer",
        "application.orchestrator.receiver",
        "application.orchestrator.reconciler",
        "application.orchestrator.transition_service",
        "application.orchestrator.evidence_admission",
        "application.orchestrator.evaluation_transition_service",
        "application.orchestrator.evaluator_runner",
        "application.orchestrator.synthesis_bundle",
        "application.orchestrator.discovery_admission_governance",
        "application.orchestrator.atomic_discovery_admission",
        "application.orchestrator.discovery_admission_coordinator",
        "application.orchestrator.validity_propagation_service",
        "application.orchestrator.review_propagation",
        "application.evidence.identity",
        "schemas.execution_observations",
        "schemas.data_explorer_contracts",
        "schemas.specialist_contracts",
        "schemas.discovery_admission_contracts",
        "schemas.validity_propagation_contracts",
        "repositories.evaluation_control_repository",
        "repositories.proposal_decision_repository",
        "repositories.discovery_admission_claim_repository",
        "repositories.discovery_repository",
        "repositories.validity_event_repository",
    ]
    violations: list[str] = []
    for root in (Path("src"), Path("tests")):
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                imported_modules: list[str] = []
                if isinstance(node, ast.ImportFrom) and node.module:
                    imported_modules.append(node.module)
                elif isinstance(node, ast.Import):
                    imported_modules.extend(alias.name for alias in node.names)
                for imported_module in imported_modules:
                    if imported_module in forbidden_imports:
                        violations.append(f"{path.as_posix()}: {imported_module}")

    assert not violations, f"Old import paths found in active code/tests: {violations}"


def test_package_s1b_execution_schema_compatibility_exports_are_removed() -> None:
    """Execution models must be imported from their canonical schemas.execution owners."""

    forbidden_exports = {
        "AnalysisFrameObservation",
        "DataExplorerFailureReason",
        "DataExplorerFailureResult",
        "DataExplorerResult",
        "DataExplorerSuccessResult",
        "EvidenceObservation",
        "ExecutionDetails",
        "ExecutionSpecification",
        "HypothesisDraft",
        "PreparedExecution",
        "TechnicalDiagnostic",
        "TechnicalRetryDisposition",
    }
    violations: list[str] = []

    contracts_path = Path("src/schemas/execution/contracts.py")
    contracts_tree = ast.parse(contracts_path.read_text(encoding="utf-8"))
    for node in ast.walk(contracts_tree):
        if isinstance(node, ast.ImportFrom) and node.module == "schemas.execution.observations":
            imported = sorted(alias.name for alias in node.names if alias.name in forbidden_exports)
            if imported:
                violations.append(f"{contracts_path.as_posix()}: re-exports {imported}")

    planner_types_path = Path("src/agents/planner/types.py")
    planner_tree = ast.parse(planner_types_path.read_text(encoding="utf-8"))
    for node in ast.walk(planner_tree):
        if isinstance(node, ast.Assign):
            names = {
                target.id
                for target in node.targets
                if isinstance(target, ast.Name) and target.id in forbidden_exports
            }
            if names:
                violations.append(
                    f"{planner_types_path.as_posix()}: aliases {sorted(names)}"
                )
        elif isinstance(node, ast.ImportFrom) and node.module == "schemas.execution.observations":
            imported = sorted(alias.name for alias in node.names if alias.name in forbidden_exports)
            if imported:
                violations.append(
                    f"{planner_types_path.as_posix()}: re-exports {imported}"
                )

    for root in (Path("src"), Path("tests")):
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not (
                    isinstance(node, ast.ImportFrom)
                    and node.module == "schemas.specialist_contracts"
                ):
                    continue
                imported = sorted(
                    alias.name for alias in node.names if alias.name in forbidden_exports
                )
                if imported:
                    violations.append(
                        f"{path.as_posix()}: imports compatibility symbols {imported}"
                    )

    assert not violations, f"Execution-schema compatibility exports remain: {violations}"


def test_package_s1b_application_dependency_directions_are_enforced() -> None:
    """Execution and Evidence contexts may depend only on their explicit neighbors."""

    evidence_allowed_execution_imports = {
        "application.execution.identity",
        "application.execution.transition_service",
    }
    violations: list[str] = []

    for path in Path("src/application/execution").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.module:
                continue
            if node.module.startswith("application.orchestrator"):
                violations.append(f"{path.as_posix()}: imports {node.module}")
            if (
                node.module.startswith("application.evidence")
                and "recovery" not in path.parts
            ):
                violations.append(f"{path.as_posix()}: imports {node.module} outside recovery")
            if node.module.startswith("agents.executor.hypothesis_analyst"):
                violations.append(f"{path.as_posix()}: imports {node.module}")

    for path in Path("src/application/evidence").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.module:
                continue
            if (
                node.module.startswith("application.execution")
                and node.module not in evidence_allowed_execution_imports
            ):
                violations.append(f"{path.as_posix()}: imports {node.module}")
            if node.module.startswith(
                (
                    "application.orchestrator",
                    "agents.executor.hypothesis_analyst",
                )
            ):
                violations.append(f"{path.as_posix()}: imports {node.module}")

    assert not violations, f"S1-B dependency-direction violations: {violations}"


def test_package_s2a_dependency_directions_are_enforced() -> None:
    """Package S2-A architecture and dependency direction invariants must hold."""

    violations: list[str] = []

    # 1. Schemas import no application or repository code
    for path in Path("src/schemas").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith(("application", "repositories")):
                    violations.append(f"{path.as_posix()}: schema imports {node.module}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(("application", "repositories")):
                        violations.append(f"{path.as_posix()}: schema imports {alias.name}")

    # 2. Repositories import no application code
    for path in Path("src/repositories").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("application"):
                    violations.append(f"{path.as_posix()}: repository imports {node.module}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("application"):
                        violations.append(f"{path.as_posix()}: repository imports {alias.name}")

    # 3. Analyst imports no application, persistence, governance, or executor peers
    for path in Path("src/agents/executor/hypothesis_analyst").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith(
                    (
                        "application",
                        "db",
                        "repositories",
                        "schemas.governance",
                        "schemas.discovery",
                        "agents.executor.dispatcher",
                        "agents.executor.registry",
                        "sqlmodel",
                    )
                ):
                    violations.append(f"{path.as_posix()}: Analyst imports {node.module}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(("application", "db", "repositories", "sqlmodel")):
                        violations.append(f"{path.as_posix()}: Analyst imports {alias.name}")

    # 4. application.evaluation does not import governance or atomic admission
    for path in Path("src/application/evaluation").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith(
                    (
                        "application.governance",
                        "schemas.governance",
                        "repositories.governance",
                        "application.discovery",
                    )
                ):
                    violations.append(f"{path.as_posix()}: evaluation imports {node.module}")

    # 5. application.governance does not invoke Analyst or depend on admission implementation
    for path in Path("src/application/governance").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith(
                    (
                        "agents.executor.hypothesis_analyst",
                        "application.discovery",
                        "repositories.discovery",
                    )
                ):
                    violations.append(f"{path.as_posix()}: governance imports {node.module}")

    assert not violations, f"S2-A dependency-direction violations: {violations}"


def test_package_s2a_compatibility_exports_and_public_repository_writers_are_removed() -> None:
    """Canonical S2-A owners must not leak through old contracts or public writers."""

    forbidden_repository_writers = {
        Path("src/repositories/evaluation/control.py"): {"stage_create", "create"},
        Path("src/repositories/governance/proposal_decision.py"): {"stage_create", "create"},
    }
    violations: list[str] = []
    for path, forbidden_names in forbidden_repository_writers.items():
        repository_tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(repository_tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name in forbidden_names
            ):
                violations.append(f"{path.as_posix()}: public writer {node.name}")

    assert not violations, f"S2-A compatibility/transaction leaks remain: {violations}"


def test_package_s2b_discovery_and_validity_modules_moved_out_of_orchestrator() -> None:
    """Discovery and validity modules must not exist under application.orchestrator."""

    forbidden_old_files = [
        "src/application/orchestrator/atomic_discovery_admission.py",
        "src/application/orchestrator/discovery_admission_coordinator.py",
        "src/application/orchestrator/validity_propagation_service.py",
        "src/application/orchestrator/review_propagation.py",
        "src/schemas/discovery_admission_contracts.py",
        "src/schemas/validity_propagation_contracts.py",
        "src/repositories/discovery_admission_claim_repository.py",
        "src/repositories/discovery_repository.py",
        "src/repositories/validity_event_repository.py",
    ]
    present = [path for path in forbidden_old_files if Path(path).exists()]
    assert not present, f"Decomposed S2-B modules still exist in old flat locations: {present}"


def test_package_s2b_dependency_directions_are_enforced() -> None:
    """Package S2-B architecture and dependency direction invariants must hold."""

    violations: list[str] = []

    # 1. Discovery admission does not invoke Analyst or depend on decision creation logic
    for path in Path("src/application/discovery").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("agents.executor.hypothesis_analyst"):
                    violations.append(f"{path.as_posix()}: discovery imports {node.module}")

    # 2. Validity propagation does not import Analyst or decision services
    for path in Path("src/application/validity").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith(
                    (
                        "agents.executor.hypothesis_analyst",
                        "application.governance.decision_service",
                    )
                ):
                    violations.append(f"{path.as_posix()}: validity imports {node.module}")

    # 3. Governance records authority/decisions but does not own admission planning.
    governance_tree = ast.parse(
        Path("src/application/governance/decision_service.py").read_text(encoding="utf-8")
    )
    if any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "create_admission_plan"
        for node in ast.walk(governance_tree)
    ):
        violations.append("application.governance: owns create_admission_plan")
    for path in Path("src/application/governance").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("application.discovery"):
                    violations.append(f"{path.as_posix()}: governance imports {node.module}")

    # 4. Canonical schema/repository layers remain dependency-inert.
    for package in ("src/schemas/discovery", "src/schemas/validity"):
        for path in Path(package).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if node.module.startswith(("application", "repositories")):
                        violations.append(f"{path.as_posix()}: schema imports {node.module}")
    for package in ("src/repositories/discovery", "src/repositories/validity"):
        for path in Path(package).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if node.module.startswith("application"):
                        violations.append(f"{path.as_posix()}: repository imports {node.module}")

    # 5. Mutable repository staging hooks are private and transaction-boundary named.
    allowed_private_hooks = {
        "_stage_enqueue_from_atomic_admission",
        "_stage_claim_from_atomic_admission",
        "_stage_cancel_from_atomic_admission",
        "_stage_invalidate_from_atomic_admission",
        "_stage_commit_from_atomic_admission",
        "_stage_create_from_atomic_admission",
        "_stage_event_from_atomic_propagation",
    }
    for package in ("src/repositories/discovery", "src/repositories/validity"):
        for path in Path(package).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name.startswith("stage_"):
                        violations.append(f"{path.as_posix()}: public stage hook {node.name}")
                    if node.name.startswith("_stage_") and node.name not in allowed_private_hooks:
                        violations.append(f"{path.as_posix()}: ambiguous stage hook {node.name}")

    # 6. Discovery and validity plan policy have one implementation owner each.
    discovery_plan = Path("src/application/discovery/admission_plan.py").read_text(
        encoding="utf-8"
    )
    if ".create_admission_plan(" in discovery_plan:
        violations.append("application.discovery.admission_plan delegates plan ownership")
    validity_service = Path("src/application/validity/propagation_service.py").read_text(
        encoding="utf-8"
    )
    for duplicate in ("_EVENT_SOURCE_ALLOWLIST =", "_EVENT_AUTHORITY ="):
        if duplicate in validity_service:
            violations.append(f"application.validity.propagation_service duplicates {duplicate}")

    assert not violations, f"S2-B dependency-direction violations: {violations}"


def test_package_s3a_table_models_have_one_definition_per_table() -> None:
    """The db.models package must not duplicate SQLModel table registrations."""

    table_owners: dict[str, list[str]] = {}
    for path in Path("src/db/models").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not (
                isinstance(node, ast.ClassDef)
                and any(
                    keyword.arg == "table"
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is True
                    for keyword in node.keywords
                )
            ):
                continue
            table_name = next(
                (
                    statement.value.value
                    for statement in node.body
                    if isinstance(statement, ast.Assign)
                    and any(
                        isinstance(target, ast.Name) and target.id == "__tablename__"
                        for target in statement.targets
                    )
                    and isinstance(statement.value, ast.Constant)
                    and isinstance(statement.value.value, str)
                ),
                None,
            )
            assert table_name is not None, f"{path.as_posix()}:{node.name} lacks __tablename__"
            table_owners.setdefault(table_name, []).append(
                f"{path.as_posix()}:{node.name}"
            )

    assert len(table_owners) == 21
    assert not {
        table_name: owners
        for table_name, owners in table_owners.items()
        if len(owners) != 1
    }

    helper_owners: dict[str, list[str]] = {
        "TimestampedRecord": [],
        "utc_now": [],
    }
    for path in Path("src/db/models").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == "TimestampedRecord":
                helper_owners[node.name].append(path.as_posix())
            elif (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "utc_now"
            ):
                helper_owners[node.name].append(path.as_posix())
    assert helper_owners == {
        "TimestampedRecord": ["src/db/models/common.py"],
        "utc_now": ["src/db/models/common.py"],
    }


def test_package_s3a_analysis_frame_writer_is_transaction_private() -> None:
    """Only Evidence admission may call the AnalysisFrame staging hook in source."""

    repository_path = Path("src/repositories/evidence/analysis_frame.py")
    repository_tree = ast.parse(repository_path.read_text(encoding="utf-8"))
    repository_class = next(
        node
        for node in repository_tree.body
        if isinstance(node, ast.ClassDef) and node.name == "AnalysisFrameRepository"
    )
    public_writers = {
        node.name
        for node in repository_class.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in {"create", "save", "update", "upsert", "stage_create", "commit"}
    }
    assert not public_writers

    staging_method = "_stage_create_from_evidence_admission"
    callers: list[str] = []
    for path in Path("src").rglob("*.py"):
        if path == repository_path:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if any(
            isinstance(node, ast.Attribute) and node.attr == staging_method
            for node in ast.walk(tree)
        ):
            callers.append(path.as_posix())
    assert callers == ["src/application/evidence/admission_service.py"]


def test_package_s3a_does_not_duplicate_bounded_context_enums() -> None:
    """Persisted enum classes stay canonically defined in schemas.enums."""

    removed_duplicate_modules = {
        Path("src/schemas/research/lifecycle.py"),
        Path("src/schemas/execution/lifecycle.py"),
        Path("src/schemas/evidence/lifecycle.py"),
    }
    assert not [path.as_posix() for path in removed_duplicate_modules if path.exists()]
