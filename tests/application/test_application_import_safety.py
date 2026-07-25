"""Fresh-process import safety for mutually adjacent application contexts."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "module_order",
    [
        ("application.evidence", "application.execution"),
        ("application.execution", "application.evidence"),
        (
            "application.evaluation",
            "application.governance",
            "application.discovery",
            "application.validity",
        ),
        (
            "application.validity",
            "application.discovery",
            "application.evaluation",
            "application.governance",
        ),
        (
            "application.governance",
            "application.discovery",
            "application.validity",
            "application.evaluation",
        ),
    ],
)
def test_adjacent_application_packages_are_import_order_independent(
    module_order: tuple[str, ...],
) -> None:
    """Package exports must not re-enter a partially initialized neighbor."""

    script = (
        "import importlib\n"
        f"for name in {module_order!r}: importlib.import_module(name)\n"
        "print('IMPORT_OK')\n"
    )
    environment = os.environ.copy()
    source_path = str(Path("src").resolve())
    environment["PYTHONPATH"] = os.pathsep.join(
        item for item in (source_path, environment.get("PYTHONPATH", "")) if item
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert completed.stdout.strip() == "IMPORT_OK"
