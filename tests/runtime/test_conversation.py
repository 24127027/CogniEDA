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

from cognieda.runtime.conversation.history import (
    ConversationHistory,
    ConversationSegment,
    ConversationTurn,
)


def _messages(request: str, response: str) -> tuple[ModelMessage, ...]:
    return (
        ModelRequest(parts=[UserPromptPart(content=request)]),
        ModelResponse(parts=[TextPart(content=response)]),
    )


def test_conversation_segment_requires_native_messages() -> None:
    with pytest.raises(ValidationError, match="at least one ModelMessage"):
        ConversationSegment(messages=())


def test_conversation_turn_requires_at_least_one_segment() -> None:
    with pytest.raises(ValidationError, match="at least one ConversationSegment"):
        ConversationTurn(segments=())


def test_conversation_turn_rejects_duplicate_segment_ids() -> None:
    segment = ConversationSegment(messages=_messages("Req", "Resp"))
    with pytest.raises(ValidationError, match="duplicate ConversationSegment IDs"):
        ConversationTurn(segments=(segment, segment))


def test_conversation_history_appends_ordered_immutable_turns() -> None:
    first_messages = _messages("First request", "First response")
    second_messages = _messages("Second request", "Second response")
    seg1 = ConversationSegment(messages=first_messages)
    seg2 = ConversationSegment(messages=second_messages)
    empty = ConversationHistory()

    first = empty.commit_segment(seg1)
    second = first.commit_segment(seg2)

    assert empty.turns == ()
    assert len(first.turns) == 1
    assert first.turns[0].segments == (seg1,)
    assert first.turns[0].messages == first_messages
    assert second.turns[:1] == first.turns
    assert second.turns[1].segments == (seg2,)
    assert second.model_messages() == [*first_messages, *second_messages]


def test_conversation_history_rejects_duplicate_turn_ids() -> None:
    turn_id = uuid4()
    segment1 = ConversationSegment(messages=_messages("Req1", "Resp1"))
    segment2 = ConversationSegment(messages=_messages("Req2", "Resp2"))
    turn1 = ConversationTurn(turn_id=turn_id, segments=(segment1,))
    turn2 = ConversationTurn(turn_id=turn_id, segments=(segment2,))

    with pytest.raises(ValidationError, match="duplicate ConversationTurn IDs"):
        ConversationHistory(turns=(turn1, turn2))


def test_conversation_history_rejects_duplicate_segment_ids_across_turns() -> None:
    segment = ConversationSegment(messages=_messages("Req", "Resp"))
    turn1 = ConversationTurn(segments=(segment,))
    turn2 = ConversationTurn(segments=(segment,))

    with pytest.raises(ValidationError, match="duplicate ConversationSegment IDs"):
        ConversationHistory(turns=(turn1, turn2))


def test_model_messages_preserves_exact_native_message_order() -> None:
    first_messages = _messages("First request", "First response")
    second_messages = _messages("Second request", "Second response")
    seg1 = ConversationSegment(messages=first_messages)
    seg2 = ConversationSegment(messages=second_messages)
    history = ConversationHistory(
        turns=(
            ConversationTurn(segments=(seg1,)),
            ConversationTurn(segments=(seg2,)),
        )
    )

    flattened = history.model_messages()

    assert flattened == [*first_messages, *second_messages]
    assert flattened[0] is first_messages[0]
    assert flattened[-1] is second_messages[-1]


def test_conversation_history_truncate_from_removes_segment_and_causal_successors() -> None:
    s1 = ConversationSegment(messages=_messages("R1", "A1"))
    s2 = ConversationSegment(messages=_messages("R2", "A2"))
    s3 = ConversationSegment(messages=_messages("R3", "A3"))

    history = (
        ConversationHistory()
        .commit_segment(s1)
        .commit_segment(s2)
        .commit_segment(s3)
    )

    assert len(history.turns) == 3
    truncated = history.truncate_from(s2.segment_id)

    assert len(truncated.turns) == 1
    assert truncated.turns[0].segments == (s1,)
    assert truncated.model_messages() == list(s1.messages)


def test_conversation_history_truncate_from_middle_segment_in_turn() -> None:
    s1 = ConversationSegment(messages=_messages("R1", "A1"))
    s2 = ConversationSegment(messages=_messages("R2", "A2"))
    s3 = ConversationSegment(messages=_messages("R3", "A3"))

    turn1 = ConversationTurn(segments=(s1, s2))
    turn2 = ConversationTurn(segments=(s3,))
    history = ConversationHistory(turns=(turn1, turn2))

    truncated = history.truncate_from(s2.segment_id)
    assert len(truncated.turns) == 1
    assert truncated.turns[0].segments == (s1,)
    assert truncated.model_messages() == list(s1.messages)


def test_conversation_history_truncate_from_missing_segment_raises() -> None:
    s1 = ConversationSegment(messages=_messages("R1", "A1"))
    history = ConversationHistory().commit_segment(s1)

    with pytest.raises(ValueError, match="not found in ConversationHistory"):
        history.truncate_from(uuid4())
