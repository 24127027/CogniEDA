from __future__ import annotations

from pathlib import Path

from cognieda.runtime.workspace import Workspace


def test_explicit_workspace_paths_derive_from_normalized_root(tmp_path: Path) -> None:
    requested_root = tmp_path / "parent" / ".." / "project-a"

    workspace = Workspace.open(requested_root)
    expected_root = (tmp_path / "project-a").resolve()

    assert workspace.root == expected_root
    assert workspace.data_dir == expected_root / "data"
    assert workspace.state_dir == expected_root / ".cognieda" / "state"
    assert workspace.session_dir == expected_root / ".cognieda" / "sessions"


def test_workspace_initialization_creates_only_required_ownership_roots(tmp_path: Path) -> None:
    workspace = Workspace.open(tmp_path / "my-study")

    assert (workspace.root / ".cognieda" / "project.toml").is_file()
    assert workspace.data_dir.is_dir()
    assert not (workspace.data_dir / "raw").exists()
    assert not (workspace.data_dir / "derived").exists()
    assert not workspace.state_dir.exists()
    assert not workspace.session_dir.exists()


def test_explicit_workspace_is_independent_of_current_working_directory(
    monkeypatch,
    tmp_path: Path,
) -> None:
    unrelated_cwd = tmp_path / "unrelated"
    explicit_root = tmp_path / "projects" / "project-b"
    unrelated_cwd.mkdir()
    monkeypatch.chdir(unrelated_cwd)

    workspace = Workspace.open(explicit_root)

    assert workspace.root == explicit_root.resolve()
    assert workspace.data_dir == explicit_root.resolve() / "data"
    assert workspace.state_dir == explicit_root.resolve() / ".cognieda" / "state"
    assert workspace.session_dir == explicit_root.resolve() / ".cognieda" / "sessions"
    assert unrelated_cwd not in workspace.data_dir.parents


def test_user_datasets_are_not_located_under_private_workspace_state(tmp_path: Path) -> None:
    workspace = Workspace.open(tmp_path / "project-c")

    assert workspace.data_dir == workspace.root / "data"
    assert workspace.data_dir != workspace.root / ".cognieda" / "data"


def test_product_repository_has_no_canonical_research_data_directory() -> None:
    project_root = Path(__file__).resolve().parents[2]

    assert not (project_root / "data").exists()
