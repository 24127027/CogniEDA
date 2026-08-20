from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import cognieda.runtime.bootstrap as bootstrap_module
from cognieda.agents.planner.dependencies import PlannerDeps
from cognieda.application.services import PlanAdmissionService
from cognieda.runtime.application import Application
from cognieda.runtime.conversation import ConversationHistory


def test_bootstrap_wires_chat_session_to_application(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "runtime.sqlite3"
    monkeypatch.setenv("COGNIEDA_DB_URL", f"sqlite:///{database_path.as_posix()}")
    captured: dict[str, Any] = {}

    class RecordingPlanner:
        def __init__(self, **dependencies: Any) -> None:
            captured["planner"] = self
            captured["planner_dependencies"] = dependencies

    monkeypatch.setattr(bootstrap_module, "Planner", RecordingPlanner)

    application = bootstrap_module.bootstrap_application(tmp_path / "workspace")

    dependencies = captured["planner_dependencies"]
    assert isinstance(application, Application)
    assert application.planner_agent is captured["planner"]
    assert isinstance(application.conversation_history, ConversationHistory)
    assert dependencies["thread_id"] == application.session_id
    assert isinstance(dependencies["deps"], PlannerDeps)
    assert isinstance(dependencies["plan_admission"], PlanAdmissionService)
    assert not hasattr(application, "_session_frames")
    assert not hasattr(application, "session_frame")
    assert not hasattr(application, "active_plans")
