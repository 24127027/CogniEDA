from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import cognieda.runtime.bootstrap as bootstrap_module
from cognieda.application.services import PlanAdmissionService
from cognieda.infrastructure.persistence.repositories import (
    ActivePlanRepository,
    SessionFrameRepository,
)
from cognieda.runtime.application import Application


def test_bootstrap_wires_session_authority_only_through_context_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "runtime.sqlite3"
    monkeypatch.setenv("COGNIEDA_DB_URL", f"sqlite:///{database_path.as_posix()}")
    captured: dict[str, Any] = {}

    class RecordingContextProvider:
        def __init__(
            self,
            *,
            session_frames: SessionFrameRepository,
            active_plans: ActivePlanRepository,
        ) -> None:
            captured["context_provider"] = self
            captured["session_frames"] = session_frames
            captured["active_plans"] = active_plans

        def materialize(self) -> None:
            raise AssertionError("Bootstrap must not materialize PlannerContext.")

    class RecordingPlanner:
        def __init__(self, **dependencies: Any) -> None:
            captured["planner"] = self
            captured["planner_dependencies"] = dependencies

    monkeypatch.setattr(
        bootstrap_module,
        "PlannerContextProvider",
        RecordingContextProvider,
    )
    monkeypatch.setattr(bootstrap_module, "Planner", RecordingPlanner)

    application = bootstrap_module.bootstrap_application(tmp_path / "workspace")

    dependencies = captured["planner_dependencies"]
    assert isinstance(application, Application)
    assert application.planner_agent is captured["planner"]
    assert isinstance(captured["session_frames"], SessionFrameRepository)
    assert isinstance(captured["active_plans"], ActivePlanRepository)
    assert dependencies["planner_context_provider"] is captured["context_provider"]
    assert isinstance(dependencies["plan_admission"], PlanAdmissionService)
    assert not hasattr(application, "_session_frames")
    assert not hasattr(application, "session_frame")
