from __future__ import annotations

from pathlib import Path

import pandas as pd

from cognieda.infrastructure.datasets import load_dataset
from cognieda.runtime.workspace import Workspace


def test_explicit_external_dataset_remains_loadable_outside_workspace(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workspace = Workspace.open(tmp_path / "workspace")
    unrelated_cwd = tmp_path / "unrelated"
    external_path = tmp_path / "shared-data" / "source.csv"
    unrelated_cwd.mkdir()
    external_path.parent.mkdir()
    pd.DataFrame({"value": [1, 2]}).to_csv(external_path, index=False)
    monkeypatch.chdir(unrelated_cwd)

    loaded = load_dataset(external_path)

    assert loaded.path == external_path.resolve()
    assert not loaded.path.is_relative_to(workspace.data_dir)
    assert loaded.dataframe["value"].tolist() == [1, 2]
