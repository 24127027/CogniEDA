from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import cognieda.runtime.bootstrap as bootstrap_module
from cognieda.agents.planner.context import PlannerContext
from cognieda.agents.planner.dependencies import PlannerToolDeps
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
    assert isinstance(dependencies["deps"], PlannerToolDeps)
    assert isinstance(dependencies["plan_admission"], PlanAdmissionService)
    assert not hasattr(application, "_session_frames")
    assert not hasattr(application, "session_frame")
    assert not hasattr(application, "active_plans")


def test_bootstrap_context_factory_materializes_session_frame_without_querying_plans(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from unittest.mock import Mock

    from sqlmodel import Session, create_engine

    from cognieda.infrastructure.persistence.repositories import (
        ActivePlanRepository,
        SessionFrameRepository,
    )
    from cognieda.schemas import Objective, SessionFrame

    database_path = tmp_path / "runtime2.sqlite3"
    db_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("COGNIEDA_DB_URL", db_url)

    class RecordingPlanner:
        def __init__(self, **dependencies: Any) -> None:
            pass

    monkeypatch.setattr(bootstrap_module, "Planner", RecordingPlanner)

    get_by_objective_mock = Mock(wraps=ActivePlanRepository.get_by_objective_id)
    monkeypatch.setattr(ActivePlanRepository, "get_by_objective_id", get_by_objective_mock)

    application = bootstrap_module.bootstrap_application(tmp_path / "workspace2")

    engine = create_engine(db_url)
    with Session(engine) as session:
        session_frames = SessionFrameRepository(session, scope_key=str(application.session_id))
        obj_1 = Objective(text="First Objective retained in frame.")
        obj_2 = Objective(text="Second Objective retained in frame.")
        frame = SessionFrame(objectives=(obj_1, obj_2))
        session_frames.save_current(frame)

    context = application.planner_context_factory()

    assert context.objectives == (obj_1, obj_2)
    assert "active_plans" not in PlannerContext.model_fields
    assert "active_plan" not in PlannerContext.model_fields
    get_by_objective_mock.assert_not_called()
