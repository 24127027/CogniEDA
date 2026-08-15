from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

from cognieda.runtime.conversation import ConversationHistory, ConversationTurn


def _messages(request: str, response: str) -> tuple[ModelMessage, ...]:
    return (
        ModelRequest(parts=[UserPromptPart(content=request)]),
        ModelResponse(parts=[TextPart(content=response)]),
    )


def test_conversation_turn_requires_native_messages() -> None:
    with pytest.raises(ValidationError, match="at least one ModelMessage"):
        ConversationTurn(messages=())


def test_conversation_history_appends_ordered_immutable_turns() -> None:
    first_messages = _messages("First request", "First response")
    second_messages = _messages("Second request", "Second response")
    empty = ConversationHistory()

    first = empty.add_turn(first_messages)
    second = first.add_turn(second_messages)

    assert empty.turns == ()
    assert len(first.turns) == 1
    assert first.turns[0].messages == first_messages
    assert second.turns[:1] == first.turns
    assert second.turns[1].messages == second_messages
    assert second.model_messages() == [*first_messages, *second_messages]


def test_conversation_history_rejects_duplicate_turn_ids() -> None:
    turn_id = uuid4()
    turn = ConversationTurn(turn_id=turn_id, messages=_messages("Request", "Response"))

    with pytest.raises(ValidationError, match="duplicate ConversationTurn IDs"):
        ConversationHistory(turns=(turn, turn))


def test_model_messages_preserves_exact_native_message_order() -> None:
    first_messages = _messages("First request", "First response")
    second_messages = _messages("Second request", "Second response")
    history = ConversationHistory(
        turns=(
            ConversationTurn(messages=first_messages),
            ConversationTurn(messages=second_messages),
        )
    )

    flattened = history.model_messages()

    assert flattened == [*first_messages, *second_messages]
    assert flattened[0] is first_messages[0]
    assert flattened[-1] is second_messages[-1]
