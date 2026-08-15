from __future__ import annotations

import asyncio
from pathlib import Path

from cognieda.cli.mock_application import MockApplication
from cognieda.runtime.events import MessageProduced
from cognieda.runtime.messages import MessageRole, MessageType


def _submit(app: MockApplication, message: str) -> MessageProduced:
    events: list[MessageProduced] = []
    app.event_bus.subscribe(MessageProduced, events.append)

    result = asyncio.run(app.submit_message(message))

    assert result is None
    assert len(events) == 1
    return events[0]


def test_mock_application_exposes_workspace_and_event_contract(tmp_path: Path) -> None:
    app = MockApplication(workspace_root=tmp_path)

    assert app.workspace.root == tmp_path.resolve()
    assert not hasattr(app.event_bus, "candidate_plan")


def test_submit_message_publishes_assistant_text_message() -> None:
    event = _submit(MockApplication(), "hello")

    assert event.message.role is MessageRole.ASSISTANT
    assert event.message.type is MessageType.TEXT
    assert "You said: hello" in str(event.message.content)


def test_submit_message_publishes_error_surface() -> None:
    event = _submit(MockApplication(), "/error broken formatter")

    assert event.message.role is MessageRole.ASSISTANT
    assert event.message.type is MessageType.ERROR
    assert event.message.content == "broken formatter"
